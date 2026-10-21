import Svg, { Defs, G, LinearGradient, Path, Rect, Stop } from "react-native-svg";
import { colors } from "@/ui/theme/tokens";

/**
 * Identité Immo+ (immoplus-identite/, docs/design/assets/) : tracés vectoriels officiels, aucune police requise.
 * Règle d'or : le « + » est bleu sur fond clair, jaune soleil sur fond sombre.
 */

function Icone() {
  return (
    <>
      <Defs>
        <LinearGradient id="immoplus-fond" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={colors.blue} />
          <Stop offset="1" stopColor={colors.blueHover} />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="512" height="512" rx="118" fill="url(#immoplus-fond)" />
      <Path d="M140 372 L140 252 L256 150 L372 252 L372 372 Z" fill={colors.white} stroke={colors.white} strokeWidth={34} strokeLinejoin="round" />
      <Path d="M256 276 L256 356" stroke={colors.sun} strokeWidth={46} strokeLinecap="round" />
      <Path d="M216 316 L296 316" stroke={colors.sun} strokeWidth={46} strokeLinecap="round" />
    </>
  );
}

/** Icône de l'application (maison blanche et « + » jaune sur fond bleu). */
export function LogoIcon({ taille = 44 }: { taille?: number }) {
  return (
    <Svg width={taille} height={taille} viewBox="0 0 512 512">
      <Icone />
    </Svg>
  );
}

interface LogotypeProps {
  /** Côté de l'icône ; le mot « Immo+ » suit la même échelle. */
  taille?: number;
  /** Mot blanc et « + » jaune sur un fond nuit ou une bannière ; sinon mot nuit et « + » bleu. */
  surFondSombre?: boolean;
}

/** Logo horizontal Immo+ (icône + mot), unique source du logo mobile. */
export function Logotype({ taille = 32, surFondSombre = false }: LogotypeProps) {
  // Cadrage serré sur le dessin (sans la marge du fichier officiel) : `taille` = hauteur de l'icône en points.
  const hauteur = (taille * 208) / 200;
  return (
    <Svg width={(hauteur * 1096) / 208} height={hauteur} viewBox="40 40 1096 208" accessible accessibilityRole="image" accessibilityLabel="Immo+">
      <G transform="translate(44,44) scale(0.390625)">
        <Icone />
      </G>
      <G transform="translate(294,219) scale(0.2127659574468085,-0.2127659574468085)" fill={surFondSombre ? colors.white : colors.night}>
          <Path transform="translate(0,0)" d="M233 702V0H62V702Z" />
          <Path transform="translate(295,0)" d="M1001 326V0H831V303Q831 357 802.5 386.5Q774 416 724 416Q674 416 645.5 386.5Q617 357 617 303V0H447V303Q447 357 418.5 386.5Q390 416 340 416Q290 416 261.5 386.5Q233 357 233 303V0H62V558H233V488Q259 523 301.0 543.5Q343 564 396 564Q459 564 508.5 537.0Q558 510 586 460Q615 506 665.0 535.0Q715 564 774 564Q878 564 939.5 501.0Q1001 438 1001 326Z" />
          <Path transform="translate(1354,0)" d="M1001 326V0H831V303Q831 357 802.5 386.5Q774 416 724 416Q674 416 645.5 386.5Q617 357 617 303V0H447V303Q447 357 418.5 386.5Q390 416 340 416Q290 416 261.5 386.5Q233 357 233 303V0H62V558H233V488Q259 523 301.0 543.5Q343 564 396 564Q459 564 508.5 537.0Q558 510 586 460Q615 506 665.0 535.0Q715 564 774 564Q878 564 939.5 501.0Q1001 438 1001 326Z" />
          <Path transform="translate(2413,0)" d="M28 279Q28 365 66.0 430.5Q104 496 170.0 531.0Q236 566 318 566Q400 566 466.0 531.0Q532 496 570.0 430.5Q608 365 608 279Q608 193 569.5 127.5Q531 62 464.5 27.0Q398 -8 316 -8Q234 -8 168.5 27.0Q103 62 65.5 127.0Q28 192 28 279ZM434 279Q434 346 400.5 382.0Q367 418 318 418Q268 418 235.0 382.5Q202 347 202 279Q202 212 234.5 176.0Q267 140 316 140Q365 140 399.5 176.0Q434 212 434 279Z" />
      </G>
      <Path d="M1042.936170212766 78.0 L1042.936170212766 210.0" stroke={surFondSombre ? colors.sun : colors.blue} strokeWidth={46} strokeLinecap="round" />
      <Path d="M976.936170212766 144.0 L1108.936170212766 144.0" stroke={surFondSombre ? colors.sun : colors.blue} strokeWidth={46} strokeLinecap="round" />
    </Svg>
  );
}
