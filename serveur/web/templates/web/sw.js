{% load immoplus %}/* Service worker d'Immo+ : rend le site installable et affiche une page claire sans réseau.
   Il ne garde AUCUNE page en mémoire (les comptes, messages et alertes restent toujours à jour et privés) : seuls la
   page « hors ligne » et les fichiers du site (CSS, JS, images, polices) sont conservés. */
"use strict";
var VERSION = "immoplus-v1";
var HORS_LIGNE = "/hors-ligne";
var FICHIERS = [HORS_LIGNE, "{% css_immoplus %}"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(FICHIERS); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (noms) { return Promise.all(noms.filter(function (n) { return n !== VERSION; }).map(function (n) { return caches.delete(n); })); })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var requete = e.request;
  if (requete.method !== "GET") return;
  var url = new URL(requete.url);
  if (url.origin !== self.location.origin) return;

  if (requete.mode === "navigate") {
    // Page demandée : le réseau d'abord ; sans réseau, la page « hors ligne ».
    e.respondWith(fetch(requete).catch(function () { return caches.match(HORS_LIGNE); }));
    return;
  }
  if (url.pathname.indexOf("/static/") === 0) {
    // Fichiers du site : déjà vus, servis tout de suite ; sinon réseau puis gardés pour la prochaine fois.
    e.respondWith(
      caches.match(requete).then(function (connu) {
        if (connu) return connu;
        return fetch(requete).then(function (reponse) {
          if (reponse.ok) {
            var copie = reponse.clone();
            caches.open(VERSION).then(function (c) { c.put(requete, copie); });
          }
          return reponse;
        });
      })
    );
  }
});
