/* Bouton « Partager » : propose les applications du téléphone (TikTok, Instagram, WhatsApp…) quand le navigateur
   sait le faire, copie le lien d'un appui, ferme le menu au clic ailleurs ou avec Échap. */
(function () {
  "use strict";
  var menus = document.querySelectorAll("[data-partage]");

  menus.forEach(function (menu) {
    var natif = menu.querySelector("[data-partage-natif]");
    var copier = menu.querySelector("[data-partage-copier]");
    var champ = menu.querySelector("[data-partage-lien]");
    var statut = menu.querySelector("[data-partage-statut]");

    if (natif && navigator.share) {
      natif.hidden = false;
      natif.addEventListener("click", function () {
        navigator.share({ title: natif.dataset.texte, text: natif.dataset.texte, url: natif.dataset.url })
          .then(function () { menu.open = false; })
          .catch(function () { /* partage annulé : le menu reste ouvert */ });
      });
    }

    function annoncer(texte) {
      if (statut) statut.textContent = texte;
    }
    if (copier && champ) {
      copier.addEventListener("click", function () {
        var secours = function () {
          champ.select();
          annoncer(document.execCommand("copy") ? "Lien copié." : "Sélectionne le lien et copie-le.");
        };
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(champ.value).then(function () { annoncer("Lien copié."); }, secours);
        } else {
          secours();
        }
      });
      champ.addEventListener("focus", function () { champ.select(); });
    }

    menu.addEventListener("toggle", function () {
      if (!menu.open) annoncer("");
      else menus.forEach(function (autre) { if (autre !== menu) autre.open = false; });
    });
  });

  document.addEventListener("click", function (e) {
    menus.forEach(function (menu) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    menus.forEach(function (menu) {
      if (menu.open) {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
  });
})();
