"""Lectures des annonces et quartiers : espace gérant, fil public, fiche, favoris, alertes."""

import base64
import datetime
import hashlib
import json
import posixpath
import re
import uuid

from django.core.cache import cache
from django.db.models import Avg, BooleanField, Count, Q
from django.db.models.expressions import RawSQL
from django.utils.dateparse import parse_datetime

from apps.accounts import selectors as comptes
from apps.core.errors import ErreurMetier
from apps.media import stockage

from .enums import Compteur, Cuisine, Eau, StatutAnnonce, StatutMedia, TypeMedia
from .models import Alert, District, Favorite, Listing, ListingMedia, Review
from .services import geo, types


def quartiers_actifs():
    return District.objects.filter(is_active=True)


RAYON_VOISINS_M = 3000


def quartiers_voisins(slugs: list[str], *, limite: int = 4) -> list[District]:
    """Quartiers actifs les plus proches des quartiers donnés (centres à moins de 3 km), du plus proche au plus loin."""
    reference = list(quartiers_actifs().filter(slug__in=slugs))
    if not reference:
        return []
    autres = quartiers_actifs().exclude(slug__in=slugs)
    distances = []
    for q in autres:
        d = min(
            geo.haversine_m(q.latitude, q.longitude, r.latitude, r.longitude) for r in reference
        )
        if d <= RAYON_VOISINS_M:
            distances.append((d, q.name, q))
    return [q for _, _, q in sorted(distances, key=lambda t: (t[0], t[1]))[:limite]]


def quartiers_avec_chambres(limite: int = 12) -> list[dict]:
    """Quartiers actifs et nombre de chambres publiées, les plus fournis d'abord (raccourcis de l'accueil)."""
    requete = (
        quartiers_actifs()
        .annotate(
            nombre=Count(
                "listings",
                filter=Q(
                    listings__status=StatutAnnonce.PUBLISHED, listings__deleted_at__isnull=True
                ),
            )
        )
        .order_by("-nombre", "sort_order", "name")[:limite]
    )
    return [{"nom": q.name, "slug": q.slug, "nombre": q.nombre} for q in requete]


def annonces_du_gerant(gerant, statut: str | None = None):
    requete = Listing.objects.filter(gerant=gerant, deleted_at__isnull=True).select_related(
        "district"
    )
    if statut:
        requete = requete.filter(status=statut)
    return requete.order_by("-updated_at")


def annonce_du_gerant(gerant, annonce_id) -> Listing | None:
    try:
        return annonces_du_gerant(gerant).filter(pk=annonce_id).first()
    except Exception:  # noqa: BLE001 - identifiant mal formé : introuvable
        return None


def statuts_publics() -> tuple[str, ...]:
    return (StatutAnnonce.PUBLISHED,)


DEBUT_DES_STATS = datetime.date(2020, 1, 1)


def stats_par_annonce(annonce_ids: list, *, jours: int = 30) -> dict:
    """{annonce_id: {'views', 'views_total', 'contacts'}} : vues sur `jours` jours et depuis toujours, vues du jour
    encore en attente comprises ; contacts sur `jours` jours."""
    from django.utils import timezone

    from apps.core import stats

    from .services import vues

    depuis = timezone.localdate() - datetime.timedelta(days=jours)
    attente = vues.en_attente(annonce_ids)
    resultats = {}
    for aid in annonce_ids:
        sid = str(aid)
        resultats[aid] = {
            "views": stats.somme("views", [sid], depuis=depuis) + attente.get(sid, 0),
            "views_total": stats.somme("views", [sid], depuis=DEBUT_DES_STATS)
            + attente.get(sid, 0),
            "contacts": stats.somme("conversations_started", [sid], depuis=depuis),
        }
    return resultats


def statistiques_annonce(annonce_id, *, jours: int) -> dict:
    """Vues, favoris et contacts d'une annonce, au total et jour par jour (même source que le tableau de bord)."""
    import datetime

    from django.utils import timezone

    from apps.core import stats

    noms = {"views": "views", "favorites": "favorites_added", "contacts": "conversations_started"}
    aujourd_hui = timezone.localdate()
    depuis = aujourd_hui - datetime.timedelta(days=jours - 1)
    valeurs = stats.serie(list(noms.values()), str(annonce_id), depuis=depuis)
    quotidien = []
    for i in range(jours):
        jour = depuis + datetime.timedelta(days=i)
        ligne = valeurs.get(jour, {})
        quotidien.append(
            {"day": jour, **{cle: ligne.get(metrique, 0) for cle, metrique in noms.items()}}
        )
    totaux = {cle: sum(j[cle] for j in quotidien) for cle in noms}
    return {"days": jours, **totaux, "daily": quotidien}


# ----------------------------------------------------------------------------- fil public (CDC §10.3)
STATUTS_VISIBLES = (StatutAnnonce.PUBLISHED, StatutAnnonce.RENTED)
_CHAMP_TRI = {
    "recent": ("published_at", True),
    "rent_asc": ("rent_amount", False),
    "rent_desc": ("rent_amount", True),
    "distance": ("distance_to_campus_m", False),
}
DELAI_CACHE_FIL_S = 60


def _version_fil() -> int:
    return cache.get("fil:version", 1)


def invalider_fil() -> None:
    """Incrémente le compteur de version : toutes les pages de fil en cache deviennent obsolètes."""
    try:
        cache.incr("fil:version")
    except ValueError:
        cache.set("fil:version", 2, None)


def _encoder_curseur(tri: str, valeur, identifiant) -> str:
    brut = json.dumps({"s": tri, "v": str(valeur), "i": str(identifiant)})
    return base64.urlsafe_b64encode(brut.encode()).decode().rstrip("=")


def _decoder_curseur(curseur: str, tri: str) -> tuple[str, str]:
    try:
        brut = base64.urlsafe_b64decode(curseur + "=" * (-len(curseur) % 4))
        donnees = json.loads(brut)
        if donnees["s"] != tri:
            raise ValueError("tri différent")
        uuid.UUID(donnees["i"])
        return donnees["v"], donnees["i"]
    except (ValueError, KeyError, TypeError) as erreur:
        raise ErreurMetier(
            "invalid_cursor", "Curseur invalide.", champs={"cursor": ["Invalide"]}
        ) from erreur


def _appliquer_criteres(requete, f: dict):
    if f["q"]:
        # Gabarit constant : le texte saisi n'entre que par les paramètres liés. La tolérance aux fautes
        # (trigrammes) ne s'applique qu'à partir de 4 caractères : en dessous, elle ramènerait trop de bruit.
        # Recherche au fil de la frappe : chaque mot compte comme un début de mot (« B », « Ba », « Bani »…) sur
        # le titre, le quartier, le repère, le type, les équipements et les autres détails (vecteur de recherche).
        # Lettres et chiffres seulement : la requête reste toujours valide.
        mots = re.findall(r"[^\W_]+", f["q"])[:8]
        prefixes = " & ".join(f"{m}:*" for m in mots)
        # Que des symboles : seule la tolérance aux fautes (plus bas) peut encore trouver.
        sql, params = "FALSE", []
        if mots:
            debut_de_mot = (
                "unaccent(lower(listings.title || ' ' || listings.landmark_text))"
                " ~ ('\\m' || unaccent(lower(%s)))"
            )
            # Repli : mots vides ou très courts (« a », « de »), ignorés par la recherche plein texte.
            sql = (
                "search_vector @@ to_tsquery('french', unaccent(%s))"
                f" OR ({' AND '.join([debut_de_mot] * len(mots))})"
            )
            params = [prefixes, *mots]
        if len(f["q"]) >= 4:
            sql += (
                " OR word_similarity(unaccent(lower(%s)), unaccent(lower(listings.title))) > 0.3"
                " OR word_similarity(unaccent(lower(%s)), unaccent(lower(listings.landmark_text))) > 0.4"
            )
            params += [f["q"], f["q"]]
        requete = requete.annotate(
            _recherche=RawSQL(  # noqa: S611  # nosec B611
                f"({sql})", params, output_field=BooleanField()
            )
        ).filter(_recherche=True)
    if f["districts"]:
        requete = requete.filter(district__slug__in=f["districts"])
    if f["types"]:
        requete = requete.filter(room_type__in=f["types"])
    if f["rent_min"] is not None:
        requete = requete.filter(rent_amount__gte=f["rent_min"])
    if f["rent_max"] is not None:
        requete = requete.filter(rent_amount__lte=f["rent_max"])
    if f["bathroom"] is not None:
        requete = requete.filter(has_private_bathroom=f["bathroom"])
    if f["water"]:
        requete = requete.filter(water_sources__overlap=f["water"])
    if f["meter"]:
        requete = requete.filter(electricity_meter__in=f["meter"])
    if f.get("kitchen"):
        requete = requete.filter(kitchen__in=f["kitchen"])
    if f["fenced"] is not None:
        requete = requete.filter(is_fenced=f["fenced"])
    if f["available_before"]:
        requete = requete.filter(available_from__lte=f["available_before"])
    if f["max_distance_m"] is not None:
        requete = requete.filter(distance_to_campus_m__lte=f["max_distance_m"])
    return requete


def _url_variante(media: ListingMedia, largeur: str | None = None) -> str | None:
    """URL d'une variante WebP d'une photo : la plus proche de `largeur`, ou la plus grande."""
    variantes = media.variants or {}
    if not variantes or not media.poster_path:
        return None
    dossier = posixpath.dirname(media.poster_path)
    if largeur is None or largeur not in variantes:
        choisi = variantes[max(variantes, key=int)]
        if largeur is not None:
            plus_proches = [v for v in variantes if int(v) >= int(largeur)]
            choisi = variantes[min(plus_proches, key=int)] if plus_proches else choisi
    else:
        choisi = variantes[largeur]
    return stockage.url_publique(posixpath.join(dossier, choisi))


def cle_image_partage(ident) -> str | None:
    """Clé de la plus grande variante de la couverture (sinon de l'affiche de la vidéo) d'une annonce visible."""
    annonce = _trouver_visible(ident)
    if annonce is None:
        return None
    medias = _medias_prets([annonce.pk]).get(annonce.pk, [])
    photos = [m for m in medias if m.kind == TypeMedia.PHOTO and m.variants and m.poster_path]
    couverture = next((m for m in photos if m.is_cover), photos[0] if photos else None)
    if couverture is not None:
        variantes = couverture.variants
        return posixpath.join(
            posixpath.dirname(couverture.poster_path), variantes[max(variantes, key=int)]
        )
    video = next((m for m in medias if m.kind == TypeMedia.VIDEO and m.poster_path), None)
    return video.poster_path if video else None


def _medias_prets(ids) -> dict:
    par_annonce: dict = {}
    for m in ListingMedia.objects.filter(
        listing_id__in=list(ids), status=StatutMedia.READY, deleted_at__isnull=True
    ).order_by("position", "created_at"):
        par_annonce.setdefault(m.listing_id, []).append(m)
    return par_annonce


def _carte(annonce: Listing, medias: list, gerants: dict) -> dict:
    photos = [m for m in medias if m.kind == TypeMedia.PHOTO]
    video = next((m for m in medias if m.kind == TypeMedia.VIDEO), None)
    couverture = next((m for m in photos if m.is_cover), photos[0] if photos else None)
    gerant = gerants.get(annonce.gerant_id, {})
    return {
        "id": annonce.pk,
        "slug": annonce.slug,
        "title": annonce.title,
        "room_type": annonce.room_type,
        "room_type_label": types.libelle(annonce.room_type),
        "district": {"name": annonce.district.name, "slug": annonce.district.slug},
        "landmark_text": annonce.landmark_text,
        "rent_amount": annonce.rent_amount,
        "rent_negotiable": annonce.rent_negotiable,
        "deposit_months": annonce.deposit_months,
        "advance_months": annonce.advance_months,
        "distance_m": geo.arrondir_50(annonce.distance_to_campus_m),
        "has_private_bathroom": annonce.has_private_bathroom,
        "is_fenced": annonce.is_fenced,
        "available_from": annonce.available_from,
        "status": annonce.status,
        "published_at": annonce.published_at,
        "cover_url": _url_variante(couverture, "480") if couverture else None,
        "video_poster_url": (
            stockage.url_publique(video.poster_path)
            if video and annonce.status == StatutAnnonce.PUBLISHED
            else None
        ),
        "has_video": bool(video) and annonce.status == StatutAnnonce.PUBLISHED,
        "video_duration_s": (
            float(video.duration_s)
            if video and annonce.status == StatutAnnonce.PUBLISHED and video.duration_s is not None
            else None
        ),
        "gerant": {
            "name": gerant.get("name"),
            "verified": gerant.get("verified", False),
        },
    }


def _cartes(annonces: list[Listing]) -> list[dict]:
    medias = _medias_prets(a.pk for a in annonces)
    gerants = comptes.gerants_publics({a.gerant_id for a in annonces})
    return [_carte(a, medias.get(a.pk, []), gerants) for a in annonces]


def similaires(annonce_id, *, limite: int = 4) -> list[dict]:
    """Chambres similaires (plan v2, S3), même source pour le site et l'API.

    Score : même quartier (3) ou quartier voisin, centres à moins de 2 km (1,5) ; même type (2) ; loyer à ± 25 % (2) ;
    distance à l'UP à moins de 1 km d'écart (1). Égalités : la plus récente d'abord. Repli : les plus récentes en ligne.
    """
    ref = Listing.objects.select_related("district").filter(pk=annonce_id).first()
    if ref is None:
        return []
    publiees = Listing.objects.filter(
        status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True
    ).exclude(pk=ref.pk)
    loyer_bas, loyer_haut = ref.rent_amount * 0.5, ref.rent_amount * 1.5
    candidates = list(
        publiees.filter(
            Q(district_id=ref.district_id)
            | Q(room_type=ref.room_type)
            | Q(rent_amount__range=(loyer_bas, loyer_haut))
        )
        .select_related("district")
        .order_by("-published_at")[:80]
    )

    def score(a: Listing) -> float:
        total = 0.0
        if a.district_id == ref.district_id:
            total += 3
        elif (
            geo.haversine_m(
                float(a.district.latitude),
                float(a.district.longitude),
                float(ref.district.latitude),
                float(ref.district.longitude),
            )
            <= 2000
        ):
            total += 1.5
        if a.room_type == ref.room_type:
            total += 2
        if abs(a.rent_amount - ref.rent_amount) <= 0.25 * ref.rent_amount:
            total += 2
        if abs(a.distance_to_campus_m - ref.distance_to_campus_m) <= 1000:
            total += 1
        return total

    classees = sorted(
        candidates,
        key=lambda a: (-score(a), -(a.published_at.timestamp() if a.published_at else 0)),
    )
    choisies = [a for a in classees if score(a) >= 2][:limite]
    if len(choisies) < limite:  # repli : les plus récentes, sans doublon
        deja = {a.pk for a in choisies}
        choisies += [
            a
            for a in publiees.select_related("district").order_by("-published_at")[: limite * 2]
            if a.pk not in deja
        ][: limite - len(choisies)]
    return _cartes(choisies)


def carte_apercu(annonce: Listing) -> dict:
    """Carte d'aperçu gérant : même rendu public, sans exiger que l'annonce soit publiée."""
    medias = _medias_prets([annonce.pk]).get(annonce.pk, [])
    gerants = comptes.gerants_publics({annonce.gerant_id})
    carte = _carte(annonce, medias, gerants)
    video = next((m for m in medias if m.kind == TypeMedia.VIDEO), None)
    carte["has_video"] = video is not None
    carte["video_duration_s"] = (
        float(video.duration_s) if video and video.duration_s is not None else None
    )
    carte["video_poster_url"] = stockage.url_publique(video.poster_path) if video else None
    return carte


def fil(filtres: dict) -> dict:
    """Fil des annonces publiées : filtres, recherche, tri, pagination par curseur ; page en cache 60 s."""
    empreinte = hashlib.sha256(
        json.dumps(filtres, sort_keys=True, default=str).encode()
    ).hexdigest()
    cle = f"fil:{_version_fil()}:{empreinte}"
    en_cache = cache.get(cle)
    if en_cache is not None:
        return en_cache
    tri = filtres["sort"]
    champ, decroissant = _CHAMP_TRI[tri]
    requete = _appliquer_criteres(
        Listing.objects.filter(
            status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True
        ).select_related("district"),
        filtres,
    )
    if filtres["cursor"]:
        valeur, identifiant = _decoder_curseur(filtres["cursor"], tri)
        if champ == "published_at":
            valeur = parse_datetime(valeur)
            if valeur is None:
                raise ErreurMetier(
                    "invalid_cursor",
                    "Curseur invalide.",
                    champs={"cursor": ["Invalide"]},
                )
        else:
            try:
                valeur = int(valeur)
            except ValueError as erreur:
                raise ErreurMetier(
                    "invalid_cursor",
                    "Curseur invalide.",
                    champs={"cursor": ["Invalide"]},
                ) from erreur
        sens = "lt" if decroissant else "gt"
        requete = requete.filter(
            Q(**{f"{champ}__{sens}": valeur}) | Q(**{champ: valeur, f"id__{sens}": identifiant})
        )
    prefixe = "-" if decroissant else ""
    lignes = list(requete.order_by(f"{prefixe}{champ}", f"{prefixe}id")[: filtres["limit"] + 1])
    suivant = None
    if len(lignes) > filtres["limit"]:
        lignes = lignes[: filtres["limit"]]
        derniere = lignes[-1]
        suivant = _encoder_curseur(
            tri,
            (
                getattr(derniere, champ).isoformat()
                if champ == "published_at"
                else getattr(derniere, champ)
            ),
            derniere.pk,
        )
    resultat = {"items": _cartes(lignes), "next_cursor": suivant}
    cache.set(cle, resultat, DELAI_CACHE_FIL_S)
    return resultat


def _trouver_visible(ident) -> Listing | None:
    requete = Listing.objects.filter(
        status__in=STATUTS_VISIBLES, deleted_at__isnull=True
    ).select_related("district")
    try:
        return requete.filter(pk=uuid.UUID(str(ident))).first()
    except ValueError:
        return requete.filter(slug=str(ident)).first()


def fiche_publique(ident) -> dict | None:
    """Fiche d'une annonce (par identifiant ou par slug). Jamais d'adresse privée ni de numéro (EF-REC-08)."""
    annonce = _trouver_visible(ident)
    if annonce is None:
        return None
    medias = _medias_prets([annonce.pk]).get(annonce.pk, [])
    louee = annonce.status == StatutAnnonce.RENTED
    sortie_medias = []
    for m in medias:
        if m.kind == TypeMedia.VIDEO:
            if louee:
                continue  # annonce louée : sans vidéo (EF-REC-10)
            sortie_medias.append(
                {
                    "id": m.pk,
                    "kind": "video",
                    "playback_url": stockage.url_publique(m.playback_path),
                    "poster_url": stockage.url_publique(m.poster_path),
                    "duration_s": (float(m.duration_s) if m.duration_s is not None else None),
                    "width": m.width,
                    "height": m.height,
                }
            )
        else:
            sortie_medias.append(
                {
                    "id": m.pk,
                    "kind": "photo",
                    "url": _url_variante(m, "960"),
                    "thumb_url": _url_variante(m, "480"),
                    "width": m.width,
                    "height": m.height,
                    "is_cover": m.is_cover,
                }
            )
    gerant = comptes.gerants_publics([annonce.gerant_id]).get(annonce.gerant_id, {})
    return {
        "id": annonce.pk,
        "slug": annonce.slug,
        "title": annonce.title,
        "room_type": annonce.room_type,
        "room_type_label": types.libelle(annonce.room_type),
        "district": {"name": annonce.district.name, "slug": annonce.district.slug},
        "landmark_text": annonce.landmark_text,
        # Position publique = centre du quartier, jamais la chambre (la position exacte ne sert qu'à la distance à l'UP).
        "latitude": geo.arrondir_position(annonce.district.latitude),
        "longitude": geo.arrondir_position(annonce.district.longitude),
        "distance_m": geo.arrondir_50(annonce.distance_to_campus_m),
        "rent_amount": annonce.rent_amount,
        "deposit_months": annonce.deposit_months,
        "advance_months": annonce.advance_months,
        "agent_fee_amount": annonce.agent_fee_amount,
        "water_deposit_amount": annonce.water_deposit_amount,
        "electricity_deposit_amount": annonce.electricity_deposit_amount,
        "available_from": annonce.available_from,
        "has_private_bathroom": annonce.has_private_bathroom,
        "is_fenced": annonce.is_fenced,
        "water_sources": list(annonce.water_sources or []),
        "water_labels": [Eau(e).label for e in annonce.water_sources or [] if e in Eau.values],
        "water_label": ", ".join(
            Eau(e).label for e in annonce.water_sources or [] if e in Eau.values
        ),
        "electricity_meter": annonce.electricity_meter,
        "electricity_label": (
            Compteur(annonce.electricity_meter).label
            if annonce.electricity_meter in Compteur.values
            else ""
        ),
        "kitchen": annonce.kitchen,
        "kitchen_label": Cuisine(annonce.kitchen).label if annonce.kitchen else "",
        "rent_negotiable": annonce.rent_negotiable,
        "description_md": annonce.description_md,
        "description_html": annonce.description_html,
        "status": annonce.status,
        "published_at": annonce.published_at,
        "last_confirmed_at": annonce.last_confirmed_at,
        "media": sortie_medias,
        "reviews": resume_avis([annonce.pk]).get(annonce.pk, {"average": None, "count": 0}),
        "gerant": {
            "id": annonce.gerant_id,
            "name": gerant.get("name"),
            "verified": gerant.get("verified", False),
            "median_response_min": gerant.get("median_response_min"),
        },
        "gerant_user_id": annonce.gerant_id,
    }


def quartier_par_slug(slug: str) -> District | None:
    return District.objects.filter(slug=slug, is_active=True).first()


def slugs_publies() -> list[tuple[str, object]]:
    """(slug, date de dernière mise à jour) des annonces visibles : plan du site."""
    return list(
        Listing.objects.filter(status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True)
        .order_by("-published_at")
        .values_list("slug", "updated_at")[:5000]
    )


def annonce_pour_messagerie(annonce_id) -> dict | None:
    """Ce dont la messagerie a besoin d'une annonce : jamais l'adresse privée (voir `adresse_privee`)."""
    ligne = (
        Listing.objects.filter(pk=annonce_id, deleted_at__isnull=True)
        .select_related("district")
        .first()
    )
    if ligne is None:
        return None
    return {
        "id": ligne.pk,
        "slug": ligne.slug,
        "title": ligne.title,
        "status": ligne.status,
        "rented_at": ligne.rented_at,
        "gerant_user_id": ligne.gerant_id,
        "district_name": ligne.district.name,
        "rent_amount": ligne.rent_amount,
    }


def annonces_pour_messagerie(ids) -> dict:
    medias = _medias_prets(ids)
    res = {}
    for a in Listing.objects.filter(pk__in=list(ids)).select_related("district"):
        m_list = medias.get(a.pk, [])
        photos = [m for m in m_list if m.kind == TypeMedia.PHOTO]
        video = next((m for m in m_list if m.kind == TypeMedia.VIDEO), None)
        couverture = next((m for m in photos if m.is_cover), photos[0] if photos else None)
        poster = _url_variante(couverture, "480") if couverture else None
        if not poster and video and video.poster_path:
            poster = stockage.url_publique(video.poster_path)
        res[a.pk] = {
            "id": a.pk,
            "slug": a.slug,
            "title": a.title,
            "status": a.status,
            "rented_at": a.rented_at,
            "gerant_user_id": a.gerant_id,
            "district_name": a.district.name,
            "rent_amount": a.rent_amount,
            "cover_url": poster,
        }
    return res


def adresse_privee(annonce_id) -> str:
    """Adresse précise, réservée aux participants d'une conversation (CDC §10.5)."""
    return (
        Listing.objects.filter(pk=annonce_id).values_list("address_private", flat=True).first()
        or ""
    )


# ----------------------------------------------------------------------------- favoris et alertes
def ids_favoris(utilisateur_id, annonce_ids) -> set:
    return set(
        Favorite.objects.filter(
            user_id=utilisateur_id, listing_id__in=list(annonce_ids)
        ).values_list("listing_id", flat=True)
    )


def favoris_de(utilisateur_id) -> list[dict]:
    """Annonces favorites, plus récemment ajoutées d'abord ; les annonces louées restent affichées."""
    liens = list(Favorite.objects.filter(user_id=utilisateur_id).order_by("-created_at")[:200])
    annonces = {
        a.pk: a
        for a in Listing.objects.filter(
            pk__in=[f.listing_id for f in liens], deleted_at__isnull=True
        ).select_related("district")
    }
    ordonnees = [annonces[f.listing_id] for f in liens if f.listing_id in annonces]
    return _cartes(ordonnees)


def cartes_visibles(annonce_ids) -> list[dict]:
    """Cartes des annonces encore visibles, dans l'ordre donné (dernières chambres consultées, plan v2)."""
    ordre = []
    for ident in annonce_ids:
        try:
            ordre.append(uuid.UUID(str(ident)))
        except ValueError:
            continue
    annonces = {
        a.pk: a
        for a in Listing.objects.filter(
            pk__in=ordre, status__in=STATUTS_VISIBLES, deleted_at__isnull=True
        ).select_related("district")
    }
    return _cartes([annonces[i] for i in ordre if i in annonces])


def alertes_de(utilisateur_id) -> list[Alert]:
    return list(Alert.objects.filter(user_id=utilisateur_id).order_by("-created_at"))


def alertes_correspondantes(annonce_id) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """(alerte, locataire) dont les critères couvrent l'annonce, calculé en SQL (CDC §8.6)."""
    annonce = Listing.objects.filter(pk=annonce_id).first()
    if annonce is None:
        return []
    requete = Alert.objects.filter(is_active=True).filter(
        Q(district_ids=[]) | Q(district_ids__contains=[annonce.district_id])
    )
    requete = requete.filter(Q(room_types=[]) | Q(room_types__contains=[annonce.room_type]))
    requete = requete.filter(Q(max_rent__isnull=True) | Q(max_rent__gte=annonce.rent_amount))
    requete = requete.filter(
        Q(max_distance_m__isnull=True) | Q(max_distance_m__gte=annonce.distance_to_campus_m)
    )
    if not annonce.has_private_bathroom:
        requete = requete.filter(private_bathroom_required=False)
    if not annonce.is_fenced:
        requete = requete.filter(fenced_required=False)
    requete = requete.filter(
        Q(water_sources=[]) | Q(water_sources__overlap=list(annonce.water_sources or []))
    )
    requete = requete.filter(
        Q(electricity_meters=[]) | Q(electricity_meters__contains=[annonce.electricity_meter])
    )
    requete = requete.filter(Q(kitchens=[]) | Q(kitchens__contains=[annonce.kitchen or "-"]))
    return list(requete.values_list("pk", "user_id"))


def nombre_pour_alerte(alerte: Alert) -> int:
    """Chambres en ligne qui correspondent aujourd'hui à une alerte (mêmes règles que `alertes_correspondantes`)."""
    requete = Listing.objects.filter(status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True)
    if alerte.district_ids:
        requete = requete.filter(district_id__in=alerte.district_ids)
    if alerte.room_types:
        requete = requete.filter(room_type__in=alerte.room_types)
    if alerte.max_rent:
        requete = requete.filter(rent_amount__lte=alerte.max_rent)
    if alerte.max_distance_m:
        requete = requete.filter(distance_to_campus_m__lte=alerte.max_distance_m)
    if alerte.private_bathroom_required:
        requete = requete.filter(has_private_bathroom=True)
    if alerte.fenced_required:
        requete = requete.filter(is_fenced=True)
    if alerte.water_sources:
        requete = requete.filter(water_sources__overlap=alerte.water_sources)
    if alerte.electricity_meters:
        requete = requete.filter(electricity_meter__in=alerte.electricity_meters)
    if alerte.kitchens:
        requete = requete.filter(kitchen__in=alerte.kitchens)
    return requete.count()


def locataires_favoris(annonce_id) -> list:
    return list(Favorite.objects.filter(listing_id=annonce_id).values_list("user_id", flat=True))


def annonce_par_id(annonce_id) -> Listing | None:
    """Annonce (objet complet) pour les décisions de modération."""
    try:
        return Listing.objects.filter(pk=uuid.UUID(str(annonce_id))).first()
    except ValueError:
        return None


def tableau_de_bord_gerant(gerant) -> dict:
    """Indicateurs de l'espace gérant : annonces par statut, vues et conversations sur 30 jours, à faire (EF-DSH)."""
    import datetime

    from django.db.models import Count
    from django.utils import timezone

    from apps.core import stats

    par_statut = dict(
        Listing.objects.filter(gerant=gerant, deleted_at__isnull=True)
        .values_list("status")
        .annotate(n=Count("id"))
        .values_list("status", "n")
    )
    publiees = list(
        Listing.objects.filter(gerant=gerant, status=StatutAnnonce.PUBLISHED).values_list(
            "id", flat=True
        )
    )
    ids = [str(i) for i in publiees]
    depuis = timezone.localdate() - datetime.timedelta(days=30)
    delai = timezone.now() - datetime.timedelta(days=7)
    a_confirmer = Listing.objects.filter(
        gerant=gerant, status=StatutAnnonce.PUBLISHED, last_confirmed_at__lt=delai
    ).count()
    from .services import vues

    toutes = [
        str(i)
        for i in Listing.objects.filter(gerant=gerant, deleted_at__isnull=True).values_list(
            "id", flat=True
        )
    ]
    attente = vues.en_attente(toutes)
    return {
        "listings_by_status": par_statut,
        "views_30d": stats.somme("views", ids, depuis=depuis) + sum(attente.get(i, 0) for i in ids),
        "views_total": stats.somme("views", toutes, depuis=DEBUT_DES_STATS) + sum(attente.values()),
        "favorites_30d": stats.somme("favorites_added", ids, depuis=depuis),
        "conversations_30d": stats.somme("conversations_started", ids, depuis=depuis),
        "to_confirm": a_confirmer,
    }


# ----------------------------------------------------------------------------- avis des locataires
def _nom_court(nom: str | None) -> str:
    """« Awa Bio » → « Awa B. » : l'avis reste personnel sans exposer le nom complet."""
    morceaux = (nom or "").split()
    if not morceaux:
        return "Locataire"
    return f"{morceaux[0]} {morceaux[1][0]}." if len(morceaux) > 1 else morceaux[0]


def resume_avis(annonce_ids) -> dict:
    """{annonce_id: {"average": 4.3, "count": 7}} sur les avis visibles (absent si aucun avis)."""
    lignes = (
        Review.objects.filter(listing_id__in=list(annonce_ids), is_hidden=False)
        .values("listing_id")
        .annotate(moyenne=Avg("rating"), nombre=Count("id"))
    )
    return {
        ligne["listing_id"]: {
            "average": round(float(ligne["moyenne"]), 1),
            "count": ligne["nombre"],
        }
        for ligne in lignes
    }


def resume_avis_gerant(gerant_id) -> dict:
    """Moyenne et nombre d'avis visibles sur toutes les chambres d'un gérant."""
    agr = Review.objects.filter(listing__gerant_id=gerant_id, is_hidden=False).aggregate(
        moyenne=Avg("rating"), nombre=Count("id")
    )
    return {
        "average": round(float(agr["moyenne"]), 1) if agr["moyenne"] is not None else None,
        "count": agr["nombre"],
    }


def avis(*, annonce_id=None, gerant_id=None, limite: int = 20) -> list[dict]:
    """Avis visibles d'une chambre ou d'un gérant, les plus récents d'abord."""
    requete = Review.objects.filter(is_hidden=False).select_related("listing")
    if annonce_id is not None:
        requete = requete.filter(listing_id=annonce_id)
    if gerant_id is not None:
        requete = requete.filter(listing__gerant_id=gerant_id)
    lignes = list(requete.order_by("-created_at")[:limite])
    noms = comptes.noms_utilisateurs({a.author_id for a in lignes})
    return [
        {
            "id": a.pk,
            "rating": a.rating,
            "comment": a.comment,
            "author_name": _nom_court(noms.get(a.author_id)),
            "listing_title": a.listing.title,
            "listing_slug": a.listing.slug,
            "created_at": a.created_at,
        }
        for a in lignes
    ]


def avis_de(utilisateur_id, annonce_id) -> dict | None:
    """L'avis de ce locataire sur cette chambre (pour le modifier), même masqué."""
    a = Review.objects.filter(author_id=utilisateur_id, listing_id=annonce_id).first()
    return {"rating": a.rating, "comment": a.comment, "is_hidden": a.is_hidden} if a else None


def avis_pour_moderation(*, masques: bool | None = None, limite: int = 200) -> list[Review]:
    requete = Review.objects.select_related("listing")
    if masques is not None:
        requete = requete.filter(is_hidden=masques)
    return list(requete.order_by("-created_at")[:limite])


def profil_gerant_public(gerant_id) -> dict | None:
    """Page publique d'un gérant : identité publique, chambres en ligne, avis (accessible depuis la messagerie)."""
    try:
        gerant_id = uuid.UUID(str(gerant_id))
    except ValueError:
        return None
    profil = comptes.gerant_public(gerant_id)
    if profil is None:
        return None
    annonces = list(
        Listing.objects.filter(
            gerant_id=gerant_id, status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True
        )
        .select_related("district")
        .order_by("-published_at")[:30]
    )
    return {
        **profil,
        "listings": _cartes(annonces),
        "reviews": resume_avis_gerant(gerant_id),
        "reviews_items": avis(gerant_id=gerant_id, limite=10),
    }
