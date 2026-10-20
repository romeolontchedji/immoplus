/* Code SMS à six cases (plan d'actions v3, E5) : un seul vrai champ (remplissage automatique du SMS, lecteurs
   d'écran), six cases dessinées par-dessus. Au 6e chiffre, le formulaire part tout seul (ou le curseur passe au
   champ suivant s'il en reste un à remplir). Code refusé : les cases se vident, le téléphone vibre, les cases
   tremblent, pour qu'aucun ancien code ne reste affiché. */
(function () {
  "use strict";
  document.querySelectorAll("[data-code-otp]").forEach(function (zone) {
    var champ = zone.querySelector("input");
    var cases = zone.querySelectorAll(".code-otp__case");
    if (!champ || cases.length !== 6) return;
    zone.classList.add("code-otp--actif");

    function dessiner() {
      var chiffres = champ.value;
      var actif = document.activeElement === champ;
      cases.forEach(function (c, i) {
        c.textContent = chiffres[i] || "";
        c.classList.toggle("code-otp__case--remplie", Boolean(chiffres[i]));
        c.classList.toggle("code-otp__case--courante", actif && i === Math.min(chiffres.length, 5));
      });
    }

    function suite() {
      var form = champ.form;
      if (!form) return;
      var vide = Array.prototype.find.call(form.elements, function (el) {
        return el !== champ && el.required && !el.value && el.type !== "hidden";
      });
      if (vide) vide.focus();
      else if (form.requestSubmit) form.requestSubmit();
      else form.submit();
    }

    champ.addEventListener("input", function () {
      var propre = champ.value.replace(/\D/g, "").slice(0, 6);
      if (propre !== champ.value) champ.value = propre;
      zone.classList.remove("code-otp--erreur", "code-otp--secousse");
      dessiner();
      if (propre.length === 6) suite();
    });
    champ.addEventListener("focus", dessiner);
    champ.addEventListener("blur", dessiner);
    zone.addEventListener("click", function () { champ.focus(); });

    if (zone.hasAttribute("data-erreur")) {
      champ.value = "";
      zone.classList.add("code-otp--secousse");
      if (navigator.vibrate) navigator.vibrate([90, 60, 90]);
      champ.focus();
    }
    dessiner();
  });
})();
