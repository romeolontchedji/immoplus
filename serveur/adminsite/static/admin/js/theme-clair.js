// Administration : thème clair seul. Django relit son choix dans localStorage puis pose data-theme (theme.js) :
// on fixe les deux pour que le thème sombre du système (tokens.css) ne s'applique jamais ici.
try {
  localStorage.setItem("theme", "light");
} catch (e) {
  // Stockage indisponible (navigation privée) : l'attribut ci-dessous suffit.
}
document.documentElement.dataset.theme = "light";
