/* Clé de secours : bouton « Copier la clé » (affiché seulement si le presse-papiers est disponible). */
(function () {
  "use strict";
  document.querySelectorAll("[data-cle-secours]").forEach(function (bloc) {
    var bouton = bloc.querySelector("[data-copier-cle]");
    var cle = bloc.querySelector("[data-cle]");
    var statut = bloc.querySelector("[data-statut-cle]");
    if (!bouton || !cle || !navigator.clipboard || !window.isSecureContext) return;
    bouton.hidden = false;
    bouton.addEventListener("click", function () {
      navigator.clipboard.writeText(cle.textContent.trim()).then(function () {
        statut.textContent = "Clé copiée. Colle-la dans un endroit sûr (notes, message à toi-même).";
      });
    });
  });
})();
