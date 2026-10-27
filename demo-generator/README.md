# Generator demonstracji WebForge — v0.1

Lokalny generator JSON → samodzielny HTML, bez pakietów zewnętrznych, API, bazy danych i płatnych usług. Nie wdraża stron i nie zmienia plików produkcyjnych. Wymaga **Node.js 20 lub nowszego** (sprawdzono na Node.js 24.19.0).

## Uruchomienie

Z katalogu głównego repozytorium:

```sh
# Odtworzenie dołączonego przykładu (plik już istnieje, stąd jawne --force).
node demo-generator/generate.mjs demo-generator/examples/firma-testowa.json --force

# Nowa firma: przygotuj własny JSON i podaj jego ścieżkę.
node demo-generator/generate.mjs /sciezka/do/nowej-firmy.json

# Testy, bez instalowania zależności.
node --test demo-generator/test/*.test.mjs

# Pomoc.
node demo-generator/generate.mjs --help
```

Alternatywnie z katalogu `demo-generator`:

```sh
npm run generate -- --force
npm test
```

Nie trzeba wykonywać `npm install`. Ścieżka wejściowego JSON jest liczona względem bieżącego katalogu terminala. Wyjście zawsze trafia do `demo-generator/generated/<slug>/index.html`, niezależnie od bieżącego katalogu. CLI nie przyjmuje dowolnego katalogu wyjściowego. Ponowny zapis tego samego adresu wymaga `--force`; błędy mają kod wyjścia 1. Nie podawaj `--force`, gdy chcesz wykryć kolizję adresów.

## Dane firmy

Przykład jest w [examples/firma-testowa.json](examples/firma-testowa.json). Firma, adres i kontakty są fikcyjne. Domeny `.invalid` nie służą do rzeczywistego kontaktu; numer zerowy także jest wyłącznie demonstracyjny.

```json
{
  "slug": "moja-firma-demo",
  "nazwa": "Przykładowa Firma TEST",
  "branza": "mechanik",
  "miasto": "Łódź",
  "opis": "Fikcyjna firma przygotowana do prezentacji projektu.",
  "uslugi": [
    { "nazwa": "Diagnostyka", "opis": "Opis przykładowej usługi." },
    "Obsługa okresowa"
  ],
  "kolory": { "akcent": "#52d6b6", "tlo": "#101c25" },
  "kontakt": {
    "telefon": "+48 000 000 000",
    "email": "kontakt@example.invalid",
    "www": "https://example.invalid/",
    "adres": "Fikcyjna 0, Łódź"
  }
}
```

| Pole | Zasady |
|---|---|
| `nazwa` | Wymagany tekst, maks. 160 znaków |
| `branza` | Wymagany identyfikator z listy poniżej |
| `miasto` | Wymagany tekst, maks. 120 znaków |
| `opis` | Wymagany tekst, maks. 2000 znaków; treść, nie HTML |
| `uslugi` | Wymagane 1–12 pozycji; tekst lub obiekt `nazwa` (maks. 120) i opcjonalny `opis` (maks. 600) |
| `kolory` | Opcjonalny obiekt; `akcent` i `tlo` w formacie `#RRGGBB`; brakujące kolory pochodzą z branży |
| `kontakt` | Wymagany obiekt z co najmniej jednym z pól `telefon`, `email`, `www`; `adres` opcjonalny |
| `slug` | Opcjonalny, maks. 100 znaków; małe litery a–z, cyfry i pojedyncze łączniki, bez ścieżek |

Numer telefonu: 7–15 cyfr, opcjonalny początkowy `+`, spacje, nawiasy i łączniki. Link strony: tylko `https://` lub `http://`, bez loginu i hasła. Każde pole kontaktu ma limit 300 znaków. Nieznane pola są odrzucane, żeby literówki nie powodowały cichego pominięcia danych.

Bez `slug` generator tworzy adres z nazwy i miasta (uwzględnia polskie znaki) oraz stabilnego, ośmioznakowego skrótu SHA-256 nazwy i miasta. Zmiana nazwy lub miasta zmienia taki adres. Jawny `slug` pozwala zachować ten sam adres; jego unikalność kontroluje autor danych. `--force` świadomie zastępuje wcześniejszy wynik.

## Osiem branż i źródła

| Identyfikator JSON | Baza istniejącego projektu |
|---|---|
| `mechanik` | `demo-mechanik.html` |
| `barber` | `demo-barber.html` |
| `stylistka` | `demo-stylistka.html` |
| `elektryk` | `demo-elektryk.html` |
| `hydraulik` | `demo-hydraulik.html` |
| `kancelaria` | `demo-kancelaria.html` |
| `restauracja` | `demo-restauracja.html` |
| `trener` | `demo-trener.html` |

Wspólny układ i CSS pochodzą z obecnych demonstracji, których style były identyczne poza kolorami. `templates/demo.html` zawiera wydzieloną kopię układu i stylów; `data/industries.json` zachowuje etykietę, kolory i CTA wszystkich ośmiu wariantów. Test porównuje te dane ze źródłowymi demonstracjami. Aktualizacje plików produkcyjnych nie przepisują automatycznie kopii szablonu.

Wygenerowane demo używa faktycznie podanych usług i opisu zamiast usług fikcyjnej firmy źródłowej. Pominięto atrapy galerii i ogólne obietnice jakości, terminów lub kwalifikacji. Nie dodaje fikcyjnych opinii ani niepotwierdzonych uprawnień. Nagłówek budowany jest z nazwy i miasta.

## Wynik i podgląd

Dołączony wynik: [generated/serwis-orbita-test/index.html](generated/serwis-orbita-test/index.html).

Otwórz HTML bezpośrednio w przeglądarce. Strona ma własny CSS, nie pobiera bibliotek, nie wymaga serwera i nie wysyła danych automatycznie. Telefon, poczta i WWW są zwykłymi odnośnikami; ich świadome kliknięcie może otworzyć aplikację lub stronę. Powroty do WebForge używają pełnych adresów i działają również z podkatalogu.

## Bezpieczeństwo i zakres v0.1

- Treści JSON są kodowane jako tekst HTML; nie można dodawać własnego HTML ani JS.
- Kolory, adresy kontaktowe i slug są walidowane przed zapisem.
- Generator odrzuca symlinki w ścieżce wyjściowej i pliku docelowym. Używaj go w zaufanym lokalnym katalogu; nie jest usługą dla wielu niezaufanych użytkowników.
- Każda strona ma `noindex, nofollow` i widoczną informację, że jest demonstracją, a nie oficjalną stroną firmy. `noindex` nie zapewnia prywatności.
- Nie ma formularza, rezerwacji, panelu, AI, pobierania danych firm, galerii zdjęć ani automatycznego wdrożenia.
- Nie ma jeszcze statusów aktywne/wyłączone i automatycznego usuwania starych wyników. Aby usunąć lokalne demo, usuń wyłącznie odpowiadający mu podkatalog `generated/<slug>`.
- Nie dodano workflow CI/CD i nie skonfigurowano hostingu, domeny ani płatnych usług. Nie kopiuj wyników na produkcję bez osobnej decyzji.
- Nie dodawaj prywatnych danych potencjalnych klientów do publicznego repozytorium. Przykłady zawierają tylko dane fikcyjne.
- Walidacja kolorów nie gwarantuje kontrastu. Przed użyciem u klienta sprawdź wygląd, kontrast, długości tekstów i rzeczywiste dane kontaktowe.

## Testy

Testy używają wbudowanego `node:test`. Obejmują osiem branż, personalizację, odnośniki wewnętrzne, brak zależności i formularzy, oznaczenia demo, `noindex`, XSS, walidację i niebezpieczne protokoły URL, polskie znaki w adresach, zapis plików, kolizje, odświeżanie, symlinki, błędy CLI i odtwarzalność dołączonego HTML. Zapis testowy odbywa się w katalogach tymczasowych usuwanych po teście.

## Następny etap

Po sprawdzeniu pierwszego przykładu: uzgodnić wygląd, ewentualnie dodać zdjęcia i obsługę wielu firm w jednym wywołaniu. Panel, statusy demonstracji i wdrożenie na osobnej subdomenie wymagają kolejnych zadań. Główna witryna i jej formularze pozostają bez zmian.
