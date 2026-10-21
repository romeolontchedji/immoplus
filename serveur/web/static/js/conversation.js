// Messagerie (plan v2, W5) : fil en bas, Entrée envoie (Maj+Entrée : nouvelle ligne ; le champ s'agrandit en CSS),
// et rafraîchissement toutes les 20 s tant que le champ est vide (pas encore de temps réel sur le site).
(function () {
  "use strict";
  var fil = document.getElementById("conv-fil");
  if (fil) { fil.scrollTop = fil.scrollHeight; }
  var champ = document.getElementById("body");
  if (!champ) { return; }
  champ.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      if (champ.value.trim()) { champ.form.requestSubmit(); }
    }
  });
  setInterval(function () {
    var menuOuvert = document.querySelector(".msg-menu[open]");
    if (!champ.value.trim() && !menuOuvert && document.visibilityState === "visible") { window.location.reload(); }
  }, 20000);
})();
