/* Éditeur d'annonce en étapes (plan d'actions v3, C4) : une étape à l'écran, sur téléphone comme sur ordinateur.
   « Suivant » vérifie les champs obligatoires de l'étape avant d'avancer. À l'ouverture, l'étape affichée est celle
   qui contient une erreur renvoyée par le serveur, sinon celle choisie par le serveur (data-etape-initiale). Sans
   script, toutes les étapes restent visibles les unes sous les autres. */
(function () {
  "use strict";
  var editeur = document.querySelector("[data-editeur]");
  if (!editeur) return;
  var etapes = Array.prototype.slice.call(editeur.querySelectorAll("[data-etape]"));
  var nav = editeur.querySelector("[data-etapes-nav]");
  if (!etapes.length) return;
  editeur.classList.add("editeur--etapes");
  if (nav) nav.hidden = false;

  function numero(etape) { return parseInt(etape.getAttribute("data-etape"), 10); }

  function afficher(n, defiler) {
    var cible = etapes.find(function (e) { return numero(e) === n; }) || etapes[0];
    etapes.forEach(function (e) { e.hidden = e !== cible; });
    if (nav) {
      nav.querySelectorAll("[data-aller]").forEach(function (b) {
        var m = parseInt(b.getAttribute("data-aller"), 10);
        b.classList.toggle("etapes-annonce__etape--courante", m === numero(cible));
        b.classList.toggle("etapes-annonce__etape--faite", m < numero(cible));
        if (m === numero(cible)) b.setAttribute("aria-current", "step");
        else b.removeAttribute("aria-current");
      });
    }
    if (defiler) editeur.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function valide(etape) {
    var champs = etape.querySelectorAll("input, select, textarea");
    for (var i = 0; i < champs.length; i += 1) {
      if (!champs[i].checkValidity()) {
        champs[i].reportValidity();
        champs[i].focus();
        return false;
      }
    }
    return true;
  }

  editeur.addEventListener("click", function (e) {
    var bouton = e.target.closest("[data-aller]");
    if (!bouton || bouton.disabled) return;
    var courante = etapes.find(function (et) { return !et.hidden; });
    var cible = parseInt(bouton.getAttribute("data-aller"), 10);
    if (courante && cible > numero(courante) && bouton.hasAttribute("data-verifier") && !valide(courante)) return;
    afficher(cible, true);
  });

  var erreur = editeur.querySelector(".etape .champ__erreur");
  var depart = erreur ? numero(erreur.closest("[data-etape]")) : parseInt(editeur.getAttribute("data-etape-initiale"), 10) || 1;
  afficher(depart, false);
})();
