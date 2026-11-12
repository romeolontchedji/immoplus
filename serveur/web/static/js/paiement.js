// Paiement KKiaPay (alerte d'un locataire, abonnement d'un gérant) : un bouton [data-payer] ouvre la fenêtre KKiaPay.
// Le serveur prépare la transaction, puis vérifie lui-même le paiement auprès de KKiaPay : ce script ne prouve rien.
(function () {
  "use strict";
  var boutons = document.querySelectorAll("[data-payer]");
  if (!boutons.length) { return; }
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

  async function payer(bouton) {
    bouton.disabled = true;
    dire("Ouverture du paiement…");
    try {
      var prep = await json("/paiement/preparer", { objet: bouton.dataset.objet, plan_code: bouton.dataset.plan || "" });
      if (!prep.ok) { dire(prep.donnees.error ? prep.donnees.error.message : "Paiement indisponible.", true); bouton.disabled = false; return; }
      await charger();
      var f = prep.donnees;
      window.addKkiapayListener("success", async function (reponse) {
        dire("Paiement reçu, vérification en cours…");
        var conf = await json("/paiement/confirmer", { reference: f.reference, transaction_id: reponse.transactionId });
        if (conf.ok) { window.location.reload(); }
        else { dire(conf.donnees.error ? conf.donnees.error.message : "Paiement non vérifié.", true); bouton.disabled = false; }
      });
      window.addKkiapayListener("failed", function () { dire("Le paiement a échoué. Tu peux réessayer.", true); bouton.disabled = false; });
      window.openKkiapayWidget({ amount: f.amount, api_key: f.key, sandbox: f.sandbox, data: f.reference, theme: "#1B44D6" });
      dire("");
    } catch (e) {
      dire("Impossible d'ouvrir le paiement. Vérifie ta connexion et réessaie.", true);
      bouton.disabled = false;
    }
  }

  boutons.forEach(function (b) { b.addEventListener("click", function () { payer(b); }); });
})();
