// Paiement KKiaPay (alerte d'un locataire, abonnement d'un gérant) : un bouton [data-payer] ouvre la fenêtre KKiaPay.
// Le serveur prépare la transaction, puis vérifie lui-même le paiement auprès de KKiaPay : ce script ne prouve rien.
(function () {
  "use strict";
  var boutons = document.querySelectorAll("[data-payer]");
  var formulaire = document.querySelector("form[data-paiement]");
  var jeton = (document.querySelector("input[name=csrfmiddlewaretoken]") || {}).value || "";
  var CLE = "alerte-brouillon";

  // Reprise : une alerte payée (crédit au compte) dont le formulaire n'est pas parti (onglet fermé, réseau coupé) se crée
  // toute seule au retour sur la page, avec les options qui avaient été choisies.
  (function reprendre() {
    var suivi = document.querySelector("[data-credits]");
    var brouillon = null;
    try { brouillon = JSON.parse(sessionStorage.getItem(CLE) || "null"); } catch (e) { brouillon = null; }
    if (!suivi || !brouillon || !(parseInt(suivi.dataset.credits, 10) > 0)) { return; }
    try { sessionStorage.removeItem(CLE); } catch (e) { /* sans stockage : rien à reprendre */ }
    var f = document.createElement("form");
    f.method = "post";
    f.hidden = true;
    var champs = [["csrfmiddlewaretoken", jeton]].concat(brouillon);
    champs.forEach(function (c) {
      var i = document.createElement("input");
      i.type = "hidden"; i.name = c[0]; i.value = c[1];
      f.appendChild(i);
    });
    document.body.appendChild(f);
    HTMLFormElement.prototype.submit.call(f);
  })();

  if (!boutons.length && !formulaire) { return; }
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
  var derniere = null; // le paiement ouvert en dernier : la fermeture de la fenêtre peut précéder le « succès »
  var ecouteurs = false;

  function fini() { if (courant) { courant.bouton.disabled = false; } courant = null; }

  async function reussi(reponse) {
    var en_cours = courant || derniere;
    if (!en_cours || en_cours.verification) { return; }
    en_cours.verification = true; // la fermeture de la fenêtre ne doit pas annuler la vérification
    dire("Paiement reçu, vérification en cours…");
    var conf = await json("/paiement/confirmer", { reference: en_cours.reference, transaction_id: reponse.transactionId });
    if (conf.ok) {
      courant = null; derniere = null;
      if (en_cours.apres) { en_cours.apres(); } else { window.location.reload(); }
    } else {
      dire(conf.donnees.error ? conf.donnees.error.message : "Paiement non vérifié.", true);
      en_cours.verification = false;
      en_cours.bouton.disabled = false;
      courant = null;
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
      derniere = courant;
      if (!ecouteurs) {
        ecouteurs = true;
        window.addKkiapayListener("success", reussi);
        window.addKkiapayListener("failed", function () { dire("Le paiement a échoué. Tu peux réessayer.", true); fini(); });
        if (window.addKkiapayCloseListener) { window.addKkiapayCloseListener(function () {
          // Laisse une seconde au « succès » qui peut arriver après la fermeture avant de rendre la main.
          setTimeout(function () { if (courant && !courant.verification) { dire(""); fini(); } }, 1500);
        }); }
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
      // Les options choisies sont gardées jusqu'à la création de l'alerte (voir « reprendre » plus haut).
      try {
        var saisie = [];
        new FormData(formulaire).forEach(function (valeur, nom) {
          if (nom !== "csrfmiddlewaretoken" && typeof valeur === "string") { saisie.push([nom, valeur]); }
        });
        sessionStorage.setItem(CLE, JSON.stringify(saisie));
      } catch (err) { /* sans stockage : le formulaire part quand même après le paiement */ }
      payer(envoi, function () {
        try { sessionStorage.removeItem(CLE); } catch (err) { /* ignoré */ }
        HTMLFormElement.prototype.submit.call(formulaire);
      });
    });
  }
  boutons.forEach(function (b) { b.addEventListener("click", function () { payer(b); }); });
})();
