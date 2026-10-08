"""Filtre PostgreSQL « adresse contenue dans un réseau » pour les plafonds par plage d'adresses (`ip << cidr`)."""

import ipaddress

from django.db.models import GenericIPAddressField, Lookup


@GenericIPAddressField.register_lookup
class DansReseau(Lookup):
    lookup_name = "dans_reseau"

    def as_sql(self, compiler, connection):
        gauche, params_gauche = self.process_lhs(compiler, connection)
        droite, params_droite = self.process_rhs(compiler, connection)
        return f"{gauche} << ({droite})::inet", [*params_gauche, *params_droite]


def plage_de(adresse: str) -> str:
    """Plage de plafonnement d'une adresse : /24 en IPv4 (réseaux mobiles et Wi-Fi partagés), /64 en IPv6."""
    ip = ipaddress.ip_address(adresse)
    longueur = 24 if ip.version == 4 else 64
    return str(ipaddress.ip_network(f"{ip}/{longueur}", strict=False))
