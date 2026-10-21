/* Listes déroulantes à choix multiples (page Alertes) : la ligne fermée résume le choix, une seule liste ouverte à
   la fois, fermeture au clic ailleurs ou avec Échap. Le formulaire refuse une alerte sans aucune option. */
(function () {
  "use strict";
  var listes = document.querySelectorAll("[data-liste-multiple]");

  function resumer(liste) {
    var texte = liste.querySelector("[data-resume]");
    var choisis = Array.prototype.map.call(liste.querySelectorAll("input:checked"), function (c) {
      return c.nextElementSibling ? c.nextElementSibling.textContent.trim() : c.value;
    });
    if (!texte) return;
    if (!choisis.length) texte.textContent = texte.dataset.vide;
    else if (choisis.length <= 2) texte.textContent = choisis.join(", ");
    else texte.textContent = choisis.slice(0, 2).join(", ") + " +" + (choisis.length - 2);
    liste.classList.toggle("liste-multiple--remplie", choisis.length > 0);
  }

  listes.forEach(function (liste) {
    resumer(liste);
    liste.addEventListener("change", function () { resumer(liste); });
    liste.addEventListener("toggle", function () {
      if (liste.open) listes.forEach(function (autre) { if (autre !== liste) autre.open = false; });
    });
  });
  document.addEventListener("click", function (e) {
    listes.forEach(function (liste) { if (liste.open && !liste.contains(e.target)) liste.open = false; });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    listes.forEach(function (liste) {
      if (liste.open) { liste.open = false; liste.querySelector("summary").focus(); }
    });
  });

  document.querySelectorAll("[data-alerte-formulaire]").forEach(function (form) {
    var erreur = form.querySelector("[data-alerte-erreur]");
    form.addEventListener("submit", function (e) {
      var coche = form.querySelector("[data-liste-multiple] input:checked");
      var valeur = Array.prototype.some.call(form.querySelectorAll("[data-critere]"), function (c) { return c.value; });
      if (coche || valeur) return;
      e.preventDefault();
      if (erreur) { erreur.hidden = false; erreur.focus(); }
    });
    form.addEventListener("change", function () { if (erreur) erreur.hidden = true; });
  });
})();
