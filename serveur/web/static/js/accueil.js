(function () {
  "use strict";
  var onglets = document.querySelectorAll(".accueil-recherche__onglet");
  var inputType = document.getElementById("input-type-hero");
  if (!onglets.length || !inputType) { return; }
  onglets.forEach(function (btn) {
    btn.addEventListener("click", function () {
      onglets.forEach(function (b) {
        b.classList.remove("accueil-recherche__onglet--actif");
        b.setAttribute("aria-selected", "false");
      });
      btn.classList.add("accueil-recherche__onglet--actif");
      btn.setAttribute("aria-selected", "true");
      inputType.value = btn.dataset.type || "";
    });
  });
})();
