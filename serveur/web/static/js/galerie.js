/* Galerie de la fiche (plan d'actions v3, B1) : une diapositive à la fois, toutes au même format. Les flèches
   passent à la suivante ou à la précédente, le compteur suit ; sur téléphone, on glisse du doigt. Sans script, la
   bande défile horizontalement. */
(function () {
  "use strict";
  document.querySelectorAll("[data-galerie]").forEach(function (galerie) {
    var piste = galerie.querySelector(".galerie__piste");
    var diapos = galerie.querySelectorAll(".galerie__diapo");
    var prec = galerie.querySelector("[data-galerie-prec]");
    var suiv = galerie.querySelector("[data-galerie-suiv]");
    var compteur = galerie.querySelector("[data-galerie-compteur]");
    if (!piste || diapos.length < 2) return;

    function index() {
      return Math.round(piste.scrollLeft / Math.max(1, piste.clientWidth));
    }
    function aller(i) {
      var cible = Math.max(0, Math.min(diapos.length - 1, i));
      diapos.forEach(function (d) {
        var video = d.querySelector("video");
        if (video && !video.paused) video.pause();
      });
      piste.scrollTo({ left: cible * piste.clientWidth, behavior: "smooth" });
    }
    function majour() {
      var i = index();
      if (compteur) compteur.textContent = i + 1 + " / " + diapos.length;
      prec.disabled = i === 0;
      suiv.disabled = i === diapos.length - 1;
    }

    prec.hidden = false;
    suiv.hidden = false;
    prec.addEventListener("click", function () { aller(index() - 1); });
    suiv.addEventListener("click", function () { aller(index() + 1); });
    piste.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { e.preventDefault(); aller(index() + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); aller(index() - 1); }
    });
    var attente = null;
    piste.addEventListener("scroll", function () {
      clearTimeout(attente);
      attente = setTimeout(majour, 60);
    });
    majour();
  });
})();
