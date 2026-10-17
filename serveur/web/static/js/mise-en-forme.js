// Barre de mise en forme de la description (décision V6) : insère le Markdown restreint accepté par le serveur
// (gras, italique, intertitre, listes) et affiche l'aperçu rendu par le serveur, déjà assaini.
(function () {
  "use strict";

  function lignesSelectionnees(champ) {
    var debut = champ.value.lastIndexOf("\n", champ.selectionStart - 1) + 1;
    var fin = champ.value.indexOf("\n", champ.selectionEnd);
    if (fin === -1) { fin = champ.value.length; }
    return { debut: debut, fin: fin, lignes: champ.value.slice(debut, fin).split("\n") };
  }

  function remplacer(champ, debut, fin, texte, selDebut, selFin) {
    champ.focus();
    champ.setRangeText(texte, debut, fin, "end");
    champ.setSelectionRange(selDebut, selFin);
    champ.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // Gras et italique : entoure la sélection (ou un exemple sélectionné) ; un second clic retire la marque.
  function entourer(champ, marque, exemple) {
    var debut = champ.selectionStart, fin = champ.selectionEnd, v = champ.value, n = marque.length;
    if (v.slice(debut - n, debut) === marque && v.slice(fin, fin + n) === marque) {
      remplacer(champ, debut - n, fin + n, v.slice(debut, fin), debut - n, fin - n);
      return;
    }
    var texte = v.slice(debut, fin) || exemple;
    remplacer(champ, debut, fin, marque + texte + marque, debut + n, debut + n + texte.length);
  }

  // Intertitre et listes : préfixe chaque ligne sélectionnée ; si toutes l'ont déjà, le retire.
  function prefixer(champ, prefixe) {
    var bloc = lignesSelectionnees(champ);
    var motif = prefixe === "1. " ? /^\d+\.\s/ : new RegExp("^" + prefixe.replace(/[#*.\-]/g, "\\$&"));
    var tous = bloc.lignes.every(function (l) { return motif.test(l); });
    var lignes = bloc.lignes.map(function (l, i) {
      if (tous) { return l.replace(motif, ""); }
      var nu = l.replace(/^(?:###\s|-\s|\d+\.\s)/, "");
      return (prefixe === "1. " ? (i + 1) + ". " : prefixe) + nu;
    });
    var texte = lignes.join("\n");
    remplacer(champ, bloc.debut, bloc.fin, texte, bloc.debut, bloc.debut + texte.length);
  }

  var ACTIONS = {
    "gras": function (c) { entourer(c, "**", "texte en gras"); },
    "italique": function (c) { entourer(c, "*", "texte en italique"); },
    "titre": function (c) { prefixer(c, "### "); },
    "liste": function (c) { prefixer(c, "- "); },
    "liste-numerotee": function (c) { prefixer(c, "1. "); }
  };

  function brancher(bloc) {
    var champ = bloc.querySelector("textarea");
    var rendu = bloc.querySelector("[data-rendu]");
    var boutonApercu = bloc.querySelector("[data-apercu]");
    var outils = bloc.querySelectorAll("[data-format]");
    var jeton = document.querySelector("input[name=csrfmiddlewaretoken]");

    outils.forEach(function (b) {
      b.addEventListener("click", function () { ACTIONS[b.dataset.format](champ); });
    });

    champ.addEventListener("keydown", function (e) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) { return; }
      var touche = e.key.toLowerCase();
      if (touche === "b" || touche === "i") {
        e.preventDefault();
        ACTIONS[touche === "b" ? "gras" : "italique"](champ);
      }
    });

    function basculer(apercu) {
      champ.hidden = apercu;
      rendu.hidden = !apercu;
      boutonApercu.setAttribute("aria-pressed", apercu ? "true" : "false");
      outils.forEach(function (b) { b.disabled = apercu; });
      if (!apercu) { champ.focus(); }
    }

    boutonApercu.addEventListener("click", async function () {
      if (!rendu.hidden) { basculer(false); return; }
      rendu.textContent = "Préparation de l'aperçu…";
      basculer(true);
      try {
        var r = await fetch("/v1/pro/markdown/preview", {
          method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": jeton ? jeton.value : "" },
          body: JSON.stringify({ markdown: champ.value })
        });
        var corps = await r.json();
        if (!r.ok) { rendu.textContent = corps.error ? corps.error.message : "Aperçu indisponible."; return; }
        // HTML produit par le serveur et assaini par nh3 (balises p, strong, em, h3, ul, ol, li, br seulement).
        rendu.innerHTML = corps.html || "<p>Rien à afficher pour l'instant.</p>";
      } catch (erreur) {
        rendu.textContent = "Aperçu indisponible : vérifie ta connexion.";
      }
    });
  }

  document.querySelectorAll("[data-mise-en-forme]").forEach(brancher);
})();
