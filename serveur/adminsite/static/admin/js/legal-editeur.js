/* Éditeur des textes légaux : barre d'outils (gras, italique, titre, liste, lien) et aperçu en direct.
   Le texte est du Markdown ; l'aperçu est rendu par le serveur avec le même moteur que le site (aucun HTML brut permis). */
(function () {
  "use strict";
  var zone = document.getElementById("legal-texte");
  var apercu = document.getElementById("legal-apercu");
  var message = document.getElementById("legal-apercu-message");
  if (!zone || !apercu) return;
  var url = zone.getAttribute("data-apercu");
  var jeton = (document.querySelector("input[name=csrfmiddlewaretoken]") || {}).value || "";
  var minuteur = null;

  function entourer(avant, apres, exemple) {
    var debut = zone.selectionStart;
    var fin = zone.selectionEnd;
    var choix = zone.value.slice(debut, fin) || exemple;
    zone.value = zone.value.slice(0, debut) + avant + choix + apres + zone.value.slice(fin);
    zone.focus();
    zone.setSelectionRange(debut + avant.length, debut + avant.length + choix.length);
    planifier();
  }

  function debutDeLigne(prefixe, exemple) {
    var debut = zone.selectionStart;
    var ligne = zone.value.lastIndexOf("\n", debut - 1) + 1;
    var finLigne = zone.value.indexOf("\n", debut);
    if (finLigne === -1) finLigne = zone.value.length;
    var texte = zone.value.slice(ligne, finLigne) || exemple;
    zone.value = zone.value.slice(0, ligne) + prefixe + texte + zone.value.slice(finLigne);
    zone.focus();
    zone.setSelectionRange(ligne + prefixe.length, ligne + prefixe.length + texte.length);
    planifier();
  }

  var actions = {
    gras: function () { entourer("**", "**", "texte en gras"); },
    italique: function () { entourer("*", "*", "texte en italique"); },
    section: function () { debutDeLigne("## ", "1. Titre de la section"); },
    liste: function () { debutDeLigne("- ", "élément de la liste"); },
    puce: function () { entourer("- **", " :** ", "Libellé"); },
    lien: function () { entourer("[", "](https://)", "texte du lien"); }
  };

  document.querySelectorAll("[data-legal-action]").forEach(function (bouton) {
    bouton.addEventListener("click", function (e) {
      e.preventDefault();
      var action = actions[bouton.getAttribute("data-legal-action")];
      if (action) action();
    });
  });

  function afficher(donnees) {
    apercu.textContent = "";
    var titre = document.createElement("h2");
    titre.textContent = donnees.title;
    apercu.appendChild(titre);
    if (donnees.summary) {
      var resume = document.createElement("p");
      resume.textContent = donnees.summary;
      apercu.appendChild(resume);
    }
    donnees.sections.forEach(function (html) {
      var bloc = document.createElement("div");
      bloc.innerHTML = html; // rendu serveur : le HTML brut est interdit dans le texte, donc échappé
      apercu.appendChild(bloc);
    });
  }

  function actualiser() {
    var corps = new FormData();
    corps.append("texte", zone.value);
    fetch(url, { method: "POST", body: corps, headers: { "X-CSRFToken": jeton }, credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, json: j }; }); })
      .then(function (r) {
        if (r.ok) {
          message.textContent = "";
          afficher(r.json);
        } else {
          message.textContent = r.json.erreur || "Aperçu impossible.";
        }
      })
      .catch(function () { message.textContent = "Aperçu indisponible pour l'instant."; });
  }

  function planifier() {
    clearTimeout(minuteur);
    minuteur = setTimeout(actualiser, 400);
  }

  zone.addEventListener("input", planifier);
  actualiser();
})();
