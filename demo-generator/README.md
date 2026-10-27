# Generator demonstracji WebForge — v0.2

Generator JSON (pojedyncza firma lub lista) → osobne strony HTML i katalog demonstracji. Bez pakietów zewnętrznych, API, bazy danych i płatnych usług. Skrypt zapisuje lokalne wyniki i nie zmienia plików produkcyjnych. Wymaga **Node.js 20 lub nowszego** (sprawdzono na Node.js 24.19.0).

**Gałąź `feature/demo-generator` jest automatycznie publikowana przez istniejącą integrację Cloudflare Pages.** Commit traktuj jak publikację: do przykładów, wyników i audytu dodawaj tylko dane fikcyjne lub przeznaczone do publicznego udostępnienia. `noindex` nie jest kontrolą dostępu. Generator nie rozpoznaje, czy podane dane są prawdziwe — odpowiada za to osoba przygotowująca JSON.

## Uruchomienie

Z katalogu głównego repozytorium:

```sh
# Wygenerowanie listy fikcyjnych firm i katalogu (ponowny przebieg niczego nie zmienia).
node demo-generator/generate.mjs demo-generator/examples/lista-firm.json

# Odświeżenie zmienionych firm z listy wymaga jawnej zgody na nadpisanie.
node demo-generator/generate.mjs demo-generator/examples/lista-firm.json --force

# Nadal działa dotychczasowy JSON pojedynczej firmy.
node demo-generator/generate.mjs demo-generator/examples/firma-testowa.json

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
npm run generate:batch
npm test
```

Nie trzeba wykonywać `npm install`. Ścieżka wejściowego JSON jest liczona względem bieżącego katalogu terminala. Wyjście zawsze trafia do `demo-generator/generated/<slug>/index.html`, niezależnie od bieżącego katalogu. Strona katalogowa powstaje w `demo-generator/generated/index.html`. CLI nie przyjmuje dowolnego katalogu wyjściowego. Istniejący identyczny HTML jest pomijany; zmieniony wymaga `--force`. Błędy mają kod wyjścia 1. Nie podawaj `--force`, gdy chcesz wykryć kolizję adresów.

## Lista firm i dodawanie kolejnych

Plik listy ma postać zwykłej tablicy od 1 do 1000 obiektów zgodnych ze schematem poniżej:

```json
[
  {
    "slug": "salon-test",
    "nazwa": "Salon TEST — firma fikcyjna",
    "branza": "barber",
    "miasto": "Poznań",
    "opis": "Fikcyjna firma do demonstracji projektu.",
    "uslugi": ["Przykładowe strzyżenie"],
    "kontakt": { "email": "salon@example.invalid" }
  },
  {
    "slug": "bistro-test",
    "nazwa": "Bistro TEST — firma fikcyjna",
    "branza": "restauracja",
    "miasto": "Gdańsk",
    "opis": "Wyłącznie przykład generatora.",
    "uslugi": ["Przykładowy catering"],
    "kontakt": { "email": "bistro@example.invalid" }
  }
]
```

1. Skopiuj obiekt w `examples/lista-firm.json` lub utwórz własny plik listy. Ustaw unikalny `slug`, publiczne dane testowe i `branza` z tabeli poniżej. Nie trzeba edytować kodu.
2. Pomiń `kolory`, aby generator sam wybrał kolory branży i wariant szablonu. Nadpisanie kolorów pozostaje opcjonalne.
3. Uruchom generator. Nowe firmy zostaną dodane, identyczne pominięte. Możesz podać samą listę nowych firm zamiast pełnej historii.
4. Otwórz `generated/index.html` i sprawdź katalog oraz strony. Strony z wcześniejszych uruchomień (także v0.1 bez manifestu) zostają i nadal występują w katalogu.
5. Po sprawdzeniu dodaj do commita JSON, nowe/zmienione HTML i katalog. Na tej gałęzi commit uruchomi istniejącą publikację Cloudflare Pages.

Pominięcie firmy na nowej liście **nie usuwa** ani nie odświeża jej poprzedniej strony. `--force` zmienia wyłącznie firmy wymienione w bieżącym wejściu. Nie ma automatycznego czyszczenia katalogów. Cała paczka jest sprawdzana przed zapisem: błędne dane, powtórzony slug lub kolizja później na liście nie zapiszą wcześniejszych firm. Niespodziewany błąd dysku w trakcie zapisu może pozostawić część ukończonych stron; po usunięciu przyczyny ponów to samo wywołanie.

Zachowanie wcześniejszych stron wymaga zachowania `generated/`. W CI z pustym katalogiem wyjściowym nie da się odzyskać stron z poprzedniego wdrożenia; dlatego gotowe fikcyjne wyniki są wersjonowane. Nie usuwaj wcześniejszych wyników w konfiguracji budowania. Nie zmieniano konfiguracji Cloudflare ani jej build command w tym zadaniu.

Generator blokuje równoległe wywołania plikiem `generated/.generator.lock`. Po zwykłym błędzie blokada jest usuwana. Po nagłym przerwaniu procesu usuń ją ręcznie dopiero po upewnieniu się, że żaden generator już nie działa. Nie dodawaj blokady do commita.

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
| `etykieta_branzy` | Opcjonalny tekst (maks. 120), np. „Agroturystyka”; pozwala adapterowi Prospect Finder użyć istniejącego układu z właściwą nazwą branży |
| `cta` | Opcjonalny tekst przycisku (maks. 120); bez HTML. Bez tych dwóch pól wynik pozostaje zgodny z v0.2 |

Numer telefonu: 7–15 cyfr, opcjonalny początkowy `+`, spacje, nawiasy i łączniki. Link strony: tylko `https://` lub `http://`, bez loginu i hasła. Każde pole kontaktu ma limit 300 znaków. Nieznane pola są odrzucane, żeby literówki nie powodowały cichego pominięcia danych.

Bez `slug` generator tworzy adres z nazwy i miasta (uwzględnia polskie znaki) oraz stabilnego, ośmioznakowego skrótu SHA-256 nazwy i miasta. Zmiana nazwy lub miasta zmienia taki adres. Jawny `slug` pozwala zachować ten sam adres; jego unikalność kontroluje autor danych. `--force` świadomie zastępuje wcześniejszy wynik.

## Osiem branż i źródła

| Identyfikator JSON | Baza istniejącego projektu | Automatyczny wariant |
|---|---|---|
| `mechanik` | `demo-mechanik.html` | `uslugowy` |
| `barber` | `demo-barber.html` | `salon` |
| `stylistka` | `demo-stylistka.html` | `salon` |
| `elektryk` | `demo-elektryk.html` | `uslugowy` |
| `hydraulik` | `demo-hydraulik.html` | `uslugowy` |
| `kancelaria` | `demo-kancelaria.html` | `ekspercki` |
| `restauracja` | `demo-restauracja.html` | `gastronomia` |
| `trener` | `demo-trener.html` | `ekspercki` |

Wspólny układ i CSS pochodzą z obecnych demonstracji, których style były identyczne poza kolorami. `templates/demo.html` jest wspólną bazą, a `templates/variants/` zawiera cztery wybierane automatycznie fragmenty branżowe. Salon ma odmienną typografię i kształt panelu, gastronomia układ oferty w dwóch kolumnach, wariant ekspercki inne proporcje sekcji otwierającej. `data/industries.json` określa wybór wariantu, etykietę, kolory i CTA. Test porównuje dane bazowe z ośmioma źródłowymi demonstracjami. Aktualizacje plików produkcyjnych nie przepisują automatycznie kopii szablonu.

Wygenerowane demo używa faktycznie podanych usług i opisu zamiast usług fikcyjnej firmy źródłowej. Pominięto atrapy galerii i ogólne obietnice jakości, terminów lub kwalifikacji. Nie dodaje fikcyjnych opinii ani niepotwierdzonych uprawnień. Nagłówek budowany jest z nazwy i miasta.

## Wynik i podgląd

Dołączony [katalog](generated/index.html) zawiera cztery fikcyjne demonstracje z [listy firm](examples/lista-firm.json), w tym dotychczasowy [przykład warsztatu](generated/serwis-orbita-test/index.html).

Otwórz HTML bezpośrednio w przeglądarce. Strona ma własny CSS, nie pobiera bibliotek, nie wymaga serwera i nie wysyła danych automatycznie. Telefon, poczta i WWW są zwykłymi odnośnikami; ich świadome kliknięcie może otworzyć aplikację lub stronę. Powroty do WebForge używają pełnych adresów i działają również z podkatalogu.

Katalog jest budowany na podstawie wszystkich istniejących podkatalogów o bezpiecznych nazwach slug zawierających `index.html`; nazwy linków pochodzą z zakodowanych tytułów stron. Nie wymaga migracji starego demo ani dodatkowego pliku danych klientów. Brakujące strony nie są linkowane. Nie umieszczaj w `generated/` obcych stron ani poufnych plików — istniejące strony są celowo wykrywane i pokazywane.

## Bezpieczeństwo i zakres v0.2

- Treści JSON są kodowane jako tekst HTML; nie można dodawać własnego HTML ani JS.
- Kolory, adresy kontaktowe i slug są walidowane przed zapisem.
- Generator odrzuca symlinki w ścieżce wyjściowej i pliku docelowym. Używaj go w zaufanym lokalnym katalogu; nie jest usługą dla wielu niezaufanych użytkowników.
- Każda strona ma `noindex, nofollow` i widoczną informację, że jest demonstracją, a nie oficjalną stroną firmy. `noindex` nie zapewnia prywatności.
- Nie ma formularza, rezerwacji, panelu, AI, pobierania danych firm, galerii zdjęć ani automatycznego wdrożenia.
- Nie ma jeszcze statusów aktywne/wyłączone i automatycznego usuwania starych wyników. Aby usunąć lokalne demo, usuń wyłącznie odpowiadający mu podkatalog `generated/<slug>`.
- Nie dodano workflow CI/CD i nie zmieniono hostingu, domeny ani płatnych usług. Obecna automatyczna publikacja gałęzi w Cloudflare Pages pozostaje aktywna według informacji właściciela.
- Nie dodawaj prywatnych danych potencjalnych klientów do publicznego repozytorium. Przykłady zawierają tylko dane fikcyjne.
- Walidacja kolorów nie gwarantuje kontrastu. Przed użyciem u klienta sprawdź wygląd, kontrast, długości tekstów i rzeczywiste dane kontaktowe.

## Testy

Testy używają wbudowanego `node:test`. Obejmują osiem branż, cztery warianty, personalizację, odnośniki wewnętrzne, brak zależności i formularzy, oznaczenia demo, `noindex`, XSS, walidację i niebezpieczne protokoły URL, polskie znaki w adresach, zapis plików, kolizje, odświeżanie, symlinki, błędy CLI oraz odtwarzalność wyników. Testy paczek sprawdzają dodawanie nowych firm, zachowanie starych stron, starsze demo bez manifestu, niezmienność pominiętych wyników, walidację całej paczki przed zapisem, blokadę równoległego procesu i katalog ze wszystkimi działającymi linkami. Testy CLI używają izolowanej kopii generatora, a zapis testowy odbywa się w katalogach tymczasowych usuwanych po teście.

## Następny etap

Po sprawdzeniu katalogu i wariantów: uzgodnić wygląd, ewentualnie dodać zdjęcia, panel lub statusy demonstracji. Nowe zmiany infrastruktury wymagają kolejnych zadań. Główna witryna i jej formularze pozostają bez zmian.
