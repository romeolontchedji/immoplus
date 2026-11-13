// Envoi de photos et de vidéos (plan v2, W3) : glisser-déposer ou choix de fichiers, contrôle du type et de la taille
// avant l'envoi, une barre de progression par fichier, envoi par morceaux de 1 Mo (protocole tus minimal, reprise).
(function () {
  "use strict";
  var zone = document.getElementById("envoi-medias");
  if (!zone) { return; }
  var annonce = zone.dataset.annonce;
  var jeton = document.querySelector("input[name=csrfmiddlewaretoken]").value;
  var etat = document.getElementById("envoi-etat");
  var liste = document.getElementById("envoi-liste");
  var depot = document.getElementById("depot-zone");
  var champ = document.getElementById("envoi-fichiers");
  var MORCEAU = 1024 * 1024;
  var MO = 1024 * 1024;
  var LIMITES = { video: 150 * MO, photo: 12 * MO };
  var TYPES = /^(video\/(mp4|quicktime|webm)|image\/(jpeg|png|webp|heic|heif))$/;

  function dire(texte) { etat.textContent = texte; }

  // « Suivant » (étape 7) reste grisé tant que des fichiers partent ou sont traités.
  function suite(actif) {
    var bouton = document.querySelector("#medias [data-aller=\"7\"]");
    if (!bouton) { return; }
    bouton.disabled = !actif;
    if (actif) { bouton.removeAttribute("aria-disabled"); } else { bouton.setAttribute("aria-disabled", "true"); }
  }

  // Mise à jour sans rechargement : on relit la page (requête GET) et on remplace seulement ce qui change (récapitulatif,
  // vignettes, bouton « Suivant », étape Publication). La zone d'envoi n'est jamais touchée : rien n'est interrompu,
  // et aucune demande « renvoyer les données » du navigateur.
  async function rafraichir() {
    try {
      var r = await fetch(window.location.pathname + "?etape=6", { credentials: "same-origin", headers: { "Accept": "text/html" } });
      if (!r.ok) { return false; }
      var doc = new DOMParser().parseFromString(await r.text(), "text/html");
      ["medias-haut", "medias-bas", "publication"].forEach(function (id) {
        var actuel = document.getElementById(id), neuf = doc.getElementById(id);
        if (actuel && neuf) { actuel.innerHTML = neuf.innerHTML; }
      });
      var z = doc.getElementById("envoi-medias");
      zone.dataset.enCours = z && z.dataset.enCours === "1" ? "1" : "0";
      liste.querySelectorAll(".depot__envoi--ok").forEach(function (li) { li.remove(); }); // désormais dans les vignettes
      return true;
    } catch (e) { return false; }
  }

  // Traitement en cours : on interroge l'API toutes les 4 s, puis on met la page à jour une fois tout prêt.
  var ATTENTE = ["uploaded", "processing"]; // un envoi « uploading » vu depuis une page neuve est interrompu
  var minuteur = null;
  function surveiller() {
    if (minuteur) { return; }
    var essais = 0;
    minuteur = setInterval(async function () {
      essais += 1;
      if (essais > 150) { clearInterval(minuteur); minuteur = null; return; } // 10 minutes : on laisse l'utilisateur agir
      try {
        var r = await fetch("/v1/pro/listings/" + annonce + "/media", { credentials: "same-origin", headers: { "Accept": "application/json" } });
        if (!r.ok) { return; }
        var medias = await r.json();
        if (!medias.some(function (m) { return ATTENTE.indexOf(m.status) !== -1; })) {
          clearInterval(minuteur); minuteur = null;
          await rafraichir();
        }
      } catch (e) { /* réseau coupé : on réessaie au prochain passage */ }
    }, 4000);
  }
  if (zone.dataset.enCours === "1") { surveiller(); }

  function ligne(fichier) {
    var li = document.createElement("li");
    li.className = "depot__envoi";
    var nom = document.createElement("span");
    nom.className = "depot__envoi-nom";
    nom.textContent = fichier.name;
    var barre = document.createElement("progress");
    barre.max = 100; barre.value = 0;
    var info = document.createElement("span");
    info.className = "depot__envoi-info";
    info.textContent = "En attente";
    li.append(nom, barre, info);
    liste.append(li);
    return {
      avancer: function (pc) { barre.value = pc; info.textContent = pc + " %"; },
      fin: function () { barre.value = 100; info.textContent = "Envoyé"; li.classList.add("depot__envoi--ok"); },
      erreur: function (texte) { info.textContent = texte; li.classList.add("depot__envoi--erreur"); }
    };
  }

  function genre(fichier) { return fichier.type.indexOf("video/") === 0 ? "video" : "photo"; }

  function verifier(fichier) {
    if (fichier.type && !TYPES.test(fichier.type)) { return "Format non accepté (vidéo MP4, MOV, WEBM ; photo JPEG, PNG, HEIC)."; }
    var max = LIMITES[genre(fichier)];
    if (fichier.size > max) { return "Fichier trop lourd (" + Math.round(max / MO) + " Mo au plus)."; }
    return null;
  }

  function json(url, corps) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": jeton },
      body: JSON.stringify(corps)
    });
  }

  async function envoyer(fichier, suivi) {
    var reponse = await json("/v1/pro/listings/" + annonce + "/media", { kind: genre(fichier), size_bytes: fichier.size });
    var media = await reponse.json();
    if (!reponse.ok) { suivi.erreur(media.error ? media.error.message : "Envoi refusé."); return false; }
    var decalage = 0;
    while (decalage < fichier.size) {
      var fin = Math.min(decalage + MORCEAU, fichier.size);
      var r;
      try {
        r = await fetch(media.upload_url, {
          method: "PATCH", credentials: "same-origin",
          headers: {
            "Tus-Resumable": "1.0.0", "Upload-Offset": String(decalage),
            "Content-Type": "application/offset+octet-stream", "X-CSRFToken": jeton
          },
          body: fichier.slice(decalage, fin)
        });
      } catch (e) {
        suivi.erreur("Connexion perdue. Renvoie le fichier : l'envoi reprendra où il s'est arrêté.");
        return false;
      }
      if (r.status === 409) { decalage = parseInt(r.headers.get("Upload-Offset"), 10); continue; }
      if (r.status !== 204) { suivi.erreur("L'envoi a échoué. Réessaie."); return false; }
      decalage = parseInt(r.headers.get("Upload-Offset"), 10);
      suivi.avancer(Math.round(decalage * 100 / fichier.size));
    }
    suivi.fin();
    return true;
  }

  async function traiter(fichiers) {
    var envoyes = 0;
    suite(false);
    dire("");
    for (var i = 0; i < fichiers.length; i++) {
      var suivi = ligne(fichiers[i]);
      var probleme = verifier(fichiers[i]);
      if (probleme) { suivi.erreur(probleme); continue; }
      if (await envoyer(fichiers[i], suivi)) { envoyes += 1; }
    }
    if (envoyes) {
      dire("Envoi terminé. Traitement en cours : « Suivant » s'activera tout seul dès que tout est prêt.");
      if (await rafraichir()) {
        if (zone.dataset.enCours === "1") { surveiller(); } else { dire(""); }
      } else {
        dire("Envoi terminé. Actualise la page pour continuer.");
        suite(true);
      }
    } else {
      suite(true); // rien n'est parti (fichiers refusés) : le serveur dira si on peut continuer
    }
  }

  champ.addEventListener("change", function () { traiter(Array.prototype.slice.call(champ.files)); });
  ["dragenter", "dragover"].forEach(function (nom) {
    depot.addEventListener(nom, function (e) { e.preventDefault(); depot.classList.add("depot__zone--survol"); });
  });
  ["dragleave", "drop"].forEach(function (nom) {
    depot.addEventListener(nom, function (e) { e.preventDefault(); depot.classList.remove("depot__zone--survol"); });
  });
  depot.addEventListener("drop", function (e) { traiter(Array.prototype.slice.call(e.dataTransfer.files)); });
  zone.classList.add("depot--actif"); // JavaScript présent : le champ natif se cache derrière la zone
})();
