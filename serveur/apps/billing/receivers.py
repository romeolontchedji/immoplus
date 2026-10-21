"""Un gérant vérifié reçoit le plan Gratuit V1 (EF-ABO-06), sans import des modèles de comptes."""

from django.dispatch import receiver

from apps.accounts.signals import gerant_verifie


@receiver(gerant_verifie, dispatch_uid="billing-plan-gratuit")
def plan_gratuit(sender, gerant_id, **kwargs):
    from . import services

    services.attribuer_gratuit(gerant_id)
