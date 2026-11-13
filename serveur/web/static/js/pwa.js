/* Application installable : enregistre le service worker et propose d'installer Immo+ sur l'écran d'accueil.
   Android et ordinateur : bouton « Installer » (le navigateur affiche sa fenêtre). iPhone et iPad : le navigateur ne
   le permet pas par un bouton, on explique le geste. Refusé = on ne redemande qu'après 14 jours. */
(function () {
  "use strict";
  var CLE = "immoplus.installer";
  var PAUSE_MS = 14 * 24 * 60 * 60 * 1000;

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () { /* le site marche quand même */ });
    });
  }

  var bandeau = document.querySelector("[data-installer]");
  if (!bandeau) return;

  function lire() { try { return window.localStorage.getItem(CLE); } catch (e) { return null; } }
  function ecrire(valeur) { try { window.localStorage.setItem(CLE, valeur); } catch (e) { /* stockage bloqué : tant pis */ } }

  var installee = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;
  if (installee) return;
  var memo = lire();
  if (memo === "installee") return;
  if (memo && Date.now() - Number(memo) < PAUSE_MS) return;

  var action = bandeau.querySelector("[data-installer-action]");
  var texte = bandeau.querySelector("[data-installer-texte]");
  var invite = null;

  function montrer() { bandeau.hidden = false; }

  bandeau.querySelector("[data-installer-fermer]").addEventListener("click", function () {
    ecrire(String(Date.now()));
    bandeau.hidden = true;
  });

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    invite = e;
    montrer();
  });
  window.addEventListener("appinstalled", function () {
    ecrire("installee");
    bandeau.hidden = true;
  });
  action.addEventListener("click", function () {
    if (!invite) return;
    invite.prompt();
    invite.userChoice.then(function (choix) {
      invite = null;
      bandeau.hidden = true;
      if (choix.outcome !== "accepted") ecrire(String(Date.now()));
    });
  });

  var ios = /iphone|ipad|ipod/i.test(window.navigator.userAgent) && !window.MSStream;
  if (ios) {
    action.hidden = true;
    texte.textContent = "Touche « Partager », puis « Sur l'écran d'accueil » : Immo+ s'ouvre en un geste, comme une application.";
    montrer();
  }
})();
