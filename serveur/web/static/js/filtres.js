/* Page Chambres : filtres appliqués en temps réel (plan d'actions v3, A3).
   Chaque changement de liste ou de case recharge seulement la zone des résultats (en-tête X-Fragment) et met
   l'adresse à jour ; la recherche par mot-clé attend une courte pause de frappe. Sans JavaScript, le formulaire
   garde son bouton « Appliquer ». */
(function () {
  "use strict";
  var form = document.querySelector("[data-filtres]");
  var zone = document.getElementById("resultats");
  if (!form || !zone || !window.fetch) return;
  form.classList.add("filtres--auto");
  // Grand écran : la colonne de filtres est toujours dépliée ; sur téléphone, elle se replie sous la recherche.
  var repli = form.querySelector(".filtres__repli");
  var large = window.matchMedia("(min-width: 1024px)");
  function deplier() { if (repli && large.matches) repli.open = true; }
  deplier();
  if (large.addEventListener) large.addEventListener("change", deplier);

  var enCours = null;
  var minuterie = null;

  function adresse(params) {
    var chaine = params.toString();
    return form.getAttribute("action") + (chaine ? "?" + chaine : "");
  }

  function parametresDuFormulaire() {
    var params = new URLSearchParams();
    new FormData(form).forEach(function (valeur, cle) {
      if (valeur !== "" && !(cle === "sort" && valeur === "recent")) params.append(cle, valeur);
    });
    return params;
  }

  function compterFiltres() {
    var badge = form.querySelector(".filtres__nombre");
    var total = 0;
    parametresDuFormulaire().forEach(function (valeur, cle) {
      if (cle !== "q" && cle !== "sort" && !(cle === "district" && form.querySelector("input[type=hidden][name=district]"))) total += 1;
    });
    var titre = form.querySelector(".filtres__titre");
    if (!titre) return;
    if (!badge && total) {
      badge = document.createElement("span");
      badge.className = "filtres__nombre";
      titre.appendChild(badge);
    }
    if (badge) {
      if (total) badge.textContent = String(total);
      else badge.remove();
    }
  }

  function charger(url) {
    if (enCours) enCours.abort();
    enCours = new AbortController();
    zone.setAttribute("aria-busy", "true");
    zone.classList.add("catalogue-contenu--chargement");
    fetch(url, { headers: { "X-Fragment": "resultats" }, cache: "no-store", signal: enCours.signal, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (html) {
        zone.innerHTML = html;
        history.replaceState(null, "", url);
        compterFiltres();
      })
      .catch(function (erreur) {
        if (erreur.name !== "AbortError") window.location.href = url; // repli : page complète
      })
      .finally(function () {
        zone.setAttribute("aria-busy", "false");
        zone.classList.remove("catalogue-contenu--chargement");
      });
  }

  function appliquer() {
    charger(adresse(parametresDuFormulaire()));
  }

  /* Remet les champs du formulaire d'accord avec une adresse (puces « retirer », « Tout effacer »). */
  function synchroniser(url) {
    var params = new URL(url, window.location.href).searchParams;
    Array.prototype.forEach.call(form.elements, function (champ) {
      if (!champ.name || champ.type === "hidden") return;
      if (champ.type === "checkbox") champ.checked = params.get(champ.name) === champ.value;
      else if (champ.tagName === "SELECT") champ.value = params.get(champ.name) || (champ.name === "sort" ? "recent" : "");
      else champ.value = params.get(champ.name) || "";
    });
  }

  form.addEventListener("change", function (e) {
    if (e.target.name === "q") return;
    appliquer();
  });
  form.addEventListener("input", function (e) {
    if (e.target.name !== "q") return;
    clearTimeout(minuterie);
    minuterie = setTimeout(appliquer, 350);
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    clearTimeout(minuterie);
    appliquer();
  });
  form.addEventListener("click", function (e) {
    var lien = e.target.closest("[data-reinitialiser]");
    if (!lien) return;
    e.preventDefault();
    synchroniser(lien.href);
    appliquer();
  });
  zone.addEventListener("click", function (e) {
    var lien = e.target.closest("[data-filtre-lien]");
    if (!lien) return;
    e.preventDefault();
    synchroniser(lien.href);
    charger(lien.href);
  });
})();
