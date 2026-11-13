"""« Équipe Immo+ » : le fil entre une personne (locataire ou gérant) et l'équipe, sur le site."""

from django.shortcuts import redirect, render

from apps.core.errors import ErreurMetier
from apps.moderation import messages_equipe as equipe

from .views_public import connecte_obligatoire


@connecte_obligatoire
def fil_equipe(request):
    u = request.user
    erreur = None
    if request.method == "POST":
        try:
            equipe.ecrire_a_l_equipe(u, request.POST.get("body", ""), objet=request.POST.get("subject", ""))
        except ErreurMetier as e:
            erreur = e.message
        else:
            return redirect("/compte/equipe?ok=envoye")
    messages = equipe.fil(u.pk)
    equipe.marquer_lus(u.pk)  # le fil vient d'être affiché : les messages de l'équipe sont lus
    return render(
        request,
        "web/equipe.html",
        {
            "titre": "Équipe Immo+",
            "messages_equipe": messages,
            "erreur": erreur,
            "envoye": request.GET.get("ok") == "envoye",
            "corps_max": equipe.CORPS_MAX,
        },
    )
