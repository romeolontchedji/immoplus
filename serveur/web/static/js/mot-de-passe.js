// Œil des champs mot de passe : affiche ou masque la saisie (le bouton reste caché sans ce script).
(function () {
  document.querySelectorAll("[data-voir-mdp]").forEach(function (bouton) {
    var champ = bouton.parentElement.querySelector("input");
    if (!champ) return;
    bouton.hidden = false;
    bouton.addEventListener("click", function () {
      var visible = champ.type === "password";
      champ.type = visible ? "text" : "password";
      bouton.setAttribute("aria-pressed", visible ? "true" : "false");
      bouton.setAttribute("aria-label", visible ? "Masquer le mot de passe" : "Afficher le mot de passe");
      champ.focus();
    });
  });
})();
