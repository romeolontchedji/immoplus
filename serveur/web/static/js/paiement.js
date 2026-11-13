// Paiement KKiaPay (alerte d'un locataire, abonnement d'un gérant) : un bouton [data-payer] ouvre la fenêtre KKiaPay.
// Le serveur prépare la transaction, puis vérifie lui-même le paiement auprès de KKiaPay : ce script ne prouve rien.
(function () {
  "use strict";
  var boutons = document.querySelectorAll("[data-payer]");
  var formulaire = document.querySelector("form[data-paiement]");
  if (!boutons.length && !formulaire) { return; }
  var jeton = (document.querySelector("input[name=csrfmiddlewaretoken]") || {}).value || "";
  var etat = document.getElementById("paiement-etat");

  function dire(texte, erreur) {
    if (!etat) { return; }
    etat.textContent = texte;
    etat.classList.toggle("texte-erreur", !!erreur);
  }

  function json(url, corps) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": jeton },
      body: JSON.stringify(corps)
    }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, donnees: d }; }); });
  }

  function charger() {
    return new Promise(function (ok, ko) {
      if (window.openKkiapayWidget) { ok(); return; }
      var s = document.createElement("script");
      s.src = "https://cdn.kkiapay.me/k.js";
      s.onload = ok;
      s.onerror = function () { ko(new Error("script")); };
      document.head.appendChild(s);
    });
  }

  // Un seul paiement à la fois : les écouteurs de la fenêtre KKiaPay sont posés une fois et lisent `courant`.
  var courant = null;
  var ecouteurs = false;

  function fini() { if (courant) { courant.bouton.disabled = false; } courant = null; }

  async function reussi(reponse) {
    if (!courant) { return; }
    var en_cours = courant;
    en_cours.verification = true; // la fermeture de la fenêtre qui suit ne doit pas annuler la vérification
    dire("Paiement reçu, vérification en cours…");
    var conf = await json("/paiement/confirmer", { reference: en_cours.reference, transaction_id: reponse.transactionId });
    if (conf.ok) {
      courant = null;
      if (en_cours.apres) { en_cours.apres(); } else { window.location.reload(); }
    } else {
      dire(conf.donnees.error ? conf.donnees.error.message : "Paiement non vérifié.", true);
      fini();
    }
  }

  async function payer(bouton, apres) {
    if (courant) { return; }
    bouton.disabled = true;
    dire("Ouverture du paiement…");
    try {
      var prep = await json("/paiement/preparer", { objet: bouton.dataset.objet, plan_code: bouton.dataset.plan || "" });
      if (!prep.ok) {
        dire(prep.donnees.error ? prep.donnees.error.message : "Paiement indisponible.", true);
        bouton.disabled = false;
        return;
      }
      await charger();
      var f = prep.donnees;
      courant = { bouton: bouton, apres: apres, reference: f.reference };
      if (!ecouteurs) {
        ecouteurs = true;
        window.addKkiapayListener("success", reussi);
        window.addKkiapayListener("failed", function () { dire("Le paiement a échoué. Tu peux réessayer.", true); fini(); });
        if (window.addKkiapayCloseListener) { window.addKkiapayCloseListener(function () { if (courant && !courant.verification) { dire(""); fini(); } }); }
      }
      window.openKkiapayWidget({ amount: f.amount, api_key: f.key, sandbox: f.sandbox, data: f.reference, theme: "#1B44D6" });
      dire("");
    } catch (e) {
      dire("Impossible d'ouvrir le paiement. Vérifie ta connexion et réessaie.", true);
      bouton.disabled = false;
    }
  }

  // « Créer l'alerte » sans crédit : on paie d'abord, puis le formulaire part tout seul avec les options choisies.
  if (formulaire) {
    formulaire.addEventListener("submit", function (e) {
      e.preventDefault();
      var envoi = formulaire.querySelector("[type=submit]");
      envoi.dataset.objet = "alerte";
      payer(envoi, function () { HTMLFormElement.prototype.submit.call(formulaire); });
    });
  }
  boutons.forEach(function (b) { b.addEventListener("click", function () { payer(b); }); });
})();
