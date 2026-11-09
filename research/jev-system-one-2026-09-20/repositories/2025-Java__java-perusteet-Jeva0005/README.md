# Viikko 1 — Java perusteet
Tämä on **yksimoduulinen Gradle-projekti**, jotta VS Code tunnistaa sen suoraan Java-projektiksi.
Tehtävät harjoituttavat muuttujia, ehtoja, silmukoita, taulukoita ja merkkijonoja.

## Tehtävät

### 1. Luvun ominaisuudet (`NumberProperties`)
Metodi `public static String describe(int n)` palauttaa jonkin seuraavista:
- `positiivinen parillinen`
- `positiivinen pariton`
- `negatiivinen parillinen`
- `negatiivinen pariton`
- `nolla`

### 2. Kolmen luvun järjestäminen (`SortThree`)
Metodi `public static String ascending(int a, int b, int c)` palauttaa luvut nousevassa järjestyksessä muodossa `a,b,c` (ei välilyöntejä).

### 3. Kertotaulu (`TimesTable`)
Metodi `public static String table(int n)` palauttaa n:n kertotaulun 1..10, rivit muodossa `n x i = tulos` ja jokaisen rivin lopussa `\n`.

### 4. Salasanayritykset (`PasswordAttempts`)
Metodi `public static String login(String[] tries)` — oikea salasana on `java123`. Tarkista **enintään kolme** ensimmäistä yritystä.
- Palauta `Tervetuloa!` jos jokin niistä on oikein.
- Muuten `Liian monta virheellistä yritystä.`

### 5. Taulukon keskiarvo ja maksimi (`ArrayStats`)
- `public static double average(int[] arr)` — palauta keskiarvo `double`-tyyppisenä, tyhjän taulukon tapauksessa `0.0`.
- `public static int max(int[] arr)` — palauta suurin arvo, tyhjän taulukon tapauksessa `Integer.MIN_VALUE`.

## Testien ajaminen

- Kaikki testit:
```bash
gradle test
```
- Yksittäinen testi:
```bash
gradle test --tests viikko1.NumberPropertiesTest
```

> Vinkki VS Codeen:
> 1) Asenna **Extension Pack for Java**, 2) varmista että JDK 21 on valittu,  
> 3) kun avaat kansion, VS Code tunnistaa `build.gradle` → hyväksy import,  
> 4) jos projekti ei heti näy, suorita **Java: Clean Java Language Server Workspace** ja avaa kansio uudelleen.
