// Envoi de photos et de vidéos par morceaux de 1 Mo (protocole tus minimal), avec reprise automatique.
(function () {
  "use strict";
  var zone = document.getElementById("envoi-medias");
  if (!zone) { return; }
  var annonce = zone.dataset.annonce;
  var jeton = document.querySelector("input[name=csrfmiddlewaretoken]").value;
  var etat = document.getElementById("envoi-etat");
  var MORCEAU = 1024 * 1024;

  function dire(texte) { etat.textContent = texte; }

  function json(url, corps) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": jeton },
      body: JSON.stringify(corps)
    });
  }

  async function envoyer(fichier) {
    var genre = fichier.type.indexOf("video/") === 0 ? "video" : "photo";
    var reponse = await json("/v1/pro/listings/" + annonce + "/media", { kind: genre, size_bytes: fichier.size });
    var media = await reponse.json();
    if (!reponse.ok) { dire(media.error ? media.error.message : "Envoi refusé."); return false; }
    var decalage = 0;
    while (decalage < fichier.size) {
      var fin = Math.min(decalage + MORCEAU, fichier.size);
      var r = await fetch(media.upload_url, {
        method: "PATCH", credentials: "same-origin",
        headers: {
          "Tus-Resumable": "1.0.0", "Upload-Offset": String(decalage),
          "Content-Type": "application/offset+octet-stream", "X-CSRFToken": jeton
        },
        body: fichier.slice(decalage, fin)
      });
      if (r.status === 409) { decalage = parseInt(r.headers.get("Upload-Offset"), 10); continue; }
      if (r.status !== 204) { dire("L'envoi a échoué. Réessaie."); return false; }
      decalage = parseInt(r.headers.get("Upload-Offset"), 10);
      dire(fichier.name + " : " + Math.round(decalage * 100 / fichier.size) + " %");
    }
    return true;
  }

  document.getElementById("envoi-fichiers").addEventListener("change", async function (evenement) {
    var fichiers = Array.prototype.slice.call(evenement.target.files);
    for (var i = 0; i < fichiers.length; i++) {
      if (!(await envoyer(fichiers[i]))) { return; }
    }
    dire("Envoi terminé. Le traitement peut prendre une minute.");
    window.location.reload();
  });
})();
