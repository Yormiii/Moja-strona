# WebForge Prospect Finder v0.1

Osobny, lokalny moduł do wyszukiwania w zaimportowanych danych, oceny i ręcznej akceptacji firm. **Python 3.10+ i SQLite z biblioteki standardowej; bez instalacji pakietów i bez płatnych API.** Panel przeglądania eksportu działa w Safari na iPadzie.

W tej wersji **nie ma pobierania firm z internetu**, skanowania stron, wysyłki, publikacji demo ani integracji Telegram. Są dwa adaptery lokalnych plików JSON: `test-json` (wyłącznie fikcyjne dane) i `public-json` (własny plik z udokumentowanymi publicznymi informacjami). To działająca baza pod kolejne źródła; interfejs `SourceAdapter.search()` pozwala dołączyć je później bez zmiany punktacji i SQLite. W przyszłości każde źródło wymaga sprawdzenia dostępu, warunków użycia i sposobu weryfikacji — niczego takiego nie podłączono teraz.

## Bezpieczny start na danych fikcyjnych

Z głównego katalogu repozytorium:

```sh
# Domyślna baza: ~/.local/share/webforge-prospects/prospects.sqlite3 — poza repozytorium.
python prospect-finder/finder.py find --input prospect-finder/fixtures/companies.json

# Szukanie według miasta (obsługa polskich znaków), województwa, całej Polski.
python prospect-finder/finder.py list --city Łódź
python prospect-finder/finder.py list --voivodeship pomorskie
python prospect-finder/finder.py list --country PL
python prospect-finder/finder.py list --industry pensjonat --category modernizacja

# Eksport — użyj nowej nazwy pliku, istniejące eksporty nie są nadpisywane.
python prospect-finder/finder.py export --format json --output ~/webforge-private/prospects.json
python prospect-finder/finder.py export --format csv --output ~/webforge-private/prospects.csv
```

Przykład ma **4 fikcyjne firmy i 1 powtórzony rekord**. Po imporcie w bazie są 4 firmy. Wszystkie nazwy są oznaczone „FIRMA FIKCYJNA TEST”, a kontakty i źródła używają `.invalid`. Źródła są atrapami testowymi, nie wynikami wyszukiwania rzeczywistych firm.

Można wybrać osobną bazę: `python prospect-finder/finder.py --db /ścieżka/poza/repo/test.sqlite3 list`. Opcja `--db` występuje przed nazwą polecenia. Dane są trwałe do ręcznego usunięcia bazy. Plik bazy i eksporty mają uprawnienia `0600` na systemach POSIX.

**Nie umieszczaj bazy, eksportów, decyzji ani rzeczywistych danych wejściowych w repozytorium.** `feature/demo-generator` automatycznie publikuje Cloudflare Pages. Program odmawia zapisu bazy i eksportów w repozytorium; adapter `public-json` także odmawia odczytu pliku danych rzeczywistych z repozytorium. Nie jest to automatyczny wykrywacz sekretów w treści: wpisuj wyłącznie potrzebne, publiczne dane firmowe i nie dodawaj poufnych uwag. `.gitignore` jest dodatkowym zabezpieczeniem, a nie magazynem prywatnych danych.

## 30 branż, lokalizacje i modernizacja

`config/industries.json` zawiera **roboczą listę 30 branż, do potwierdzenia**. Zatwierdzonej wcześniejszej listy nie odnaleziono w repozytorium. Lista obejmuje usługi lokalne, beauty, motoryzację, budowę/remonty, rolnictwo, agroturystykę, noclegi i gastronomię. Pole `status` jawnie opisuje ten stan. Podmień etykiety/identyfikatory lub dodaj branże w JSON, bez zmiany kodu; istniejące identyfikatory użyte w bazie należy zachować lub osobno migrować.

`demo_template` przypisuje branży jeden z ośmiu istniejących profili wizualnych generatora. Nie oznacza zmiany rzeczywistej branży: adapter przekazuje dodatkową poprawną etykietę i neutralne CTA. Dla wszystkich 30 profili sprawdzono zgodność wejścia z generatorem.

`config/locations.json`: 16 województw (identyfikatory bez znaków diakrytycznych), kraj `PL` i przykładowe zapisane wyszukiwania. Miasto może być dowolnym tekstem. Filtry łączą się: miasto + województwo rozróżniają miejscowości o tej samej nazwie. Nazwa miasta jest porównywana bez wielkości liter i znaków diakrytycznych. Wzorce w `saved_searches` to konfiguracja do skopiowania jako flagi CLI, nie geokoder ani baza wszystkich miejscowości.

Kategoria `modernizacja` jest **niezależna od branży**: zwraca firmy z aktualnym, udokumentowanym problemem istniejącej strony. Brak strony trafia do zwykłych wyników, a nie do modernizacji. Dane nieustalone ani przeterminowane nie są traktowane jako potwierdzony problem.

```sh
python prospect-finder/finder.py config
python prospect-finder/finder.py --help
python prospect-finder/finder.py find --help
```

## Format danych i źródła

Pełny przykład: `fixtures/companies.json`. Plik adaptera ma `dataset_type: "fictional"` lub `"public"` i tablicę `records`. Źródła konfiguruje się w `config/sources.json`; można dodać kolejne pliki JSON jako nowe wpisy tego samego typu. Nowy typ zdalnego adaptera wymaga implementacji interfejsu w kodzie. Obecna wersja nie wykonuje połączeń HTTP.

Każdy rekord wymaga:

- `name`, `industry`, `city`, `voivodeship`, `country: "PL"`, opcjonalnie `address` i `website`;
- `source: {provider, id, url}` — identyfikator firmy w źródle i link;
- `last_verified_at` w formacie `YYYY-MM-DD` (nie z przyszłości) oraz jawnego `fictional: true/false`;
- opcjonalnych `contacts: [{kind: "email"/"phone", value, source_url, verified_at}]` — każdy kontakt ma własne źródło i datę;
- `activity_signs: [{description, source_url, observed_at}]` — udokumentowane oznaki bieżącej działalności, np. aktualny wpis; brak wpisów oznacza stan nieustalony;
- `facts` opisanych poniżej; można pominąć je w całości, wtedy brak punktów nie oznacza negatywnej oceny firmy;
- opcjonalnych, potwierdzonych `services` (lista do 12 tekstów) i `description` potrzebnych do późniejszego szkicu demo.

Każdy fakt to `{value, source_url, verified_at, note}`. Obsługiwane klucze:

| Fakt | Wartość |
|---|---|
| `website_status` | `missing`, `present`, `unknown` |
| `outdated`, `mobile_issues`, `unclear_offer`, `technical_issues` | `true`, `false`, `null` |
| `sales_potential` | `low`, `medium`, `high`, `unknown` |

Nieznane pola są odrzucane, także `status`, `assessment`, `contact_permission` i pola sekretów w imporcie. Źródło nie może samo zaakceptować firmy lub nadać zgody na kontakt. `website: null` bez dowodu oznacza **nieustalony stan**, nie potwierdzony brak strony. Źródła/WWW wymagają HTTP/HTTPS bez hasła, loginu, query i fragmentu — w v0.1 stosuj stabilne publiczne linki. Daty i oceny pochodzą z dokumentacji importu; program nie twierdzi, że sam zweryfikował je w sieci.

```sh
# Własny plik tylko z rzeczywiście publicznymi, udokumentowanymi danymi, poza repo.
python prospect-finder/finder.py find --source public-json --input ~/webforge-private/public-data.json --city Łódź
```

## Punktacja 0–100 i niepewność

Konfiguracja: `config/scoring.json`. **Wynik to priorytet ręcznej weryfikacji, nie prawdopodobieństwo zakupu.** Każdy składnik zachowuje uzasadnienie i dowody. Fakty starsze niż 180 dni nie dają punktów; wynik jest przeliczany przy odczycie/eksporcie. Wartość `coverage_percent` opisuje pokrycie udokumentowanych kryteriów, nie pewność statystyczną. Nie normalizujemy niskiej liczby znanych faktów do wysokiego wyniku.

| Składnik | Maks. punkty |
|---|---:|
| Potwierdzony brak strony **albo** potrzeby istniejącej strony | 50 |
| W tym przestarzałość / mobile / nieczytelna oferta / technika | 15 / 15 / 10 / 10 |
| Aktualne oznaki działalności | 20 |
| Udokumentowany potencjał sprzedażowy: niski / średni / wysoki | 10 / 20 / 30 |

Obie ścieżki potrzeby strony są rozłączne — nie sumujemy braku strony z jej usterkami. Maksimum to `50 + 20 + 30 = 100`. Potencjał jest jawną, uzasadnioną oceną przeglądającego/źródła, a nie domysłem modelu. Bez informacji o aktywności wynik tej części wynosi 0, ale `activity_state` pozostaje **nieustalone**, a nie „nieaktywna”.

## SQLite, deduplikacja i statusy

SQLite przechowuje rekord, wszystkie źródła, kontakty z pochodzeniem, oceniane fakty, status, historię decyzji i zablokowane zdarzenia przyszłej automatyzacji. Wynik jest obliczany na bieżąco z faktów i konfiguracji.

Deduplikacja używa identyfikatora w źródle albo znormalizowanej nazwy + kraju + województwa + miasta + adresu. Dane fikcyjne i rzeczywiste są oddzielnymi tożsamościami. Nie łączymy oddziałów tylko dlatego, że mają tę samą domenę lub centralny telefon. Rekordy z różnych źródeł o różnych nazwach/adresach wymagają ręcznej analizy; to konserwatywna deduplikacja, nie inteligentne rozpoznawanie wszystkich wariantów nazw. Kolizje dwóch różnych istniejących tożsamości wstrzymują transakcję.

Ponowny import aktualizuje dane i scala pochodzenie bez resetowania statusu; starszy import nie nadpisuje nowszych pól. Wszystkie rekordy paczki są walidowane przed transakcją. Nie ma kasowania rekordów ani automatycznego czyszczenia.

Statusy: **znaleziony → do weryfikacji → zaakceptowany → demo gotowe → kontakt dozwolony → kontaktowany → zainteresowany → klient**. Odrzucenie jest możliwe wcześniej, a rekord odrzucony można ponownie skierować do weryfikacji. W CLI używaj identyfikatorów z podkreśleniami (`do_weryfikacji`, `demo_gotowe`, `kontakt_dozwolony`). `kontakt_dozwolony` można też ustawić po akceptacji bez etapu demo. Przeskakiwanie etapów i nieznane statusy są blokowane.

```sh
python prospect-finder/finder.py review 1 --status do_weryfikacji --reason "Sprawdzam źródła"
python prospect-finder/finder.py review 1 --status zaakceptowany --reason "Potwierdzono dane i sens przygotowania propozycji"
```

Status **kontakt dozwolony** wymaga osobnego pliku z `{source_url, verified_at, note}` potwierdzającego zweryfikowaną podstawę kontaktu, np. udokumentowane zapytanie firmy. Publiczny adres nie nadaje tego statusu automatycznie. To kontrola procesu, nie automatyczna ocena prawna. Potwierdzenie jest związane z bieżącymi kanałami kontaktu i wygasa po czasie świeżości; zmiana kanałów blokuje oznaczenie „kontaktowany”. W tej wersji oznaczenie „kontaktowany” to wyłącznie ręczny wpis — nie wysyła wiadomości.

```sh
python prospect-finder/finder.py review 1 --status kontakt_dozwolony --reason "Ręcznie sprawdzona podstawa" --permission-file ~/webforge-private/permission.json
```

## Praca z iPada

1. Na komputerze lub prywatnym środowisku z Pythonem wykonaj import i eksport JSON. Baza pozostaje tam lokalnie; iPad nie musi uruchamiać SQLite ani Pythona.
2. Otwórz `prospect-finder/panel.html` przez istniejący statyczny podgląd gałęzi, jeśli udostępnia ten katalog. Ścieżka zależy od katalogu publikacji Cloudflare; nie zmieniano jego konfiguracji. Panel składa się tylko z HTML/CSS/JS i może działać z dowolnego zaufanego statycznego serwera. Lokalnie można użyć `python -m http.server 8000 --bind 127.0.0.1 --directory prospect-finder` i na tym komputerze wejść na `http://127.0.0.1:8000/panel.html`; nie wystawiaj bazy ani prywatnego katalogu przez serwer.
3. W Safari wybierz **Otwórz eksport JSON** z Plików. Na próbę można pobrać `fixtures/panel-demo.json` — wyłącznie fikcyjne dane. Panel filtruje nazwę/miasto, branżę, województwo, status i modernizację, sortuje wg punktów, pokazuje dowody, daty i źródła.
4. Wskaż nowy status i uzasadnienie. **Dodaj decyzję do pliku** nie zmienia bazy. Pobierz decyzje i przekaż je do lokalnego środowiska. Dane nie są wysyłane przez panel; nie używa cookies, localStorage, fetch ani zewnętrznych usług. Link do źródła otwiera się tylko po świadomym kliknięciu.
5. Zastosuj plik i wykonaj nowy eksport:

```sh
python prospect-finder/finder.py apply-decisions --input ~/webforge-private/webforge-decisions.json
python prospect-finder/finder.py export --output ~/webforge-private/prospects-next.json
```

Decyzje są stosowane transakcyjnie, z kontrolą `expected_status`: jeśli baza zmieniła się od eksportu, cały plik jest odrzucony i trzeba odświeżyć dane. W panelu kontakt dozwolony wymaga dodatkowego uzasadnienia, źródła i daty; backend sprawdza je ponownie. Wyniki punktacji są aktualne na moment eksportu, nie są przeliczane w Safari. To **offline-first przegląd i pliki decyzji, nie wieloużytkownikowy panel online**; nie dodano publicznego serwera SQLite ani synchronizacji. W pełni samodzielna praca wyłącznie z iPada bez środowiska Python wymaga kolejnego etapu.

## Most do generatora i przygotowanie automatyzacji

```sh
python prospect-finder/finder.py demo-input 1 --output ~/webforge-private/demo-draft.json
```

Adapter działa tylko dla zaakceptowanych rekordów i dalszych pozytywnych statusów. Wymaga potwierdzonych `services`, `description` oraz aktualnego kontaktu lub strony WWW. **Przejście do statusu zaakceptowany sprawdza te wymagania**, aby każdy nowo zaakceptowany rekord dało się przekształcić bez wymyślania treści. Jeśli danych brakuje, zwraca jasny błąd; po upływie czasu świeżości kontaktu może być potrzebna ponowna weryfikacja. Dla wszystkich 30 branż tworzy poprawne wejście istniejącego generatora: profil wizualny, rzeczywista etykieta branży, neutralne CTA, nazwa, miasto, opis, usługi i kontakty.

**Polecenie zapisuje tylko JSON poza repozytorium. Nie uruchamia generatora, nie tworzy HTML i nie publikuje demo.** Nie przekazuj szkiców rzeczywistych firm do automatycznie publikowanego katalogu generatora w tym etapie. Dwa opcjonalne pola `etykieta_branzy` i `cta` to jedyna zmiana generatora; istniejące wejścia, kolory, układy i wyniki pozostają zgodne.

`config/automation.json` opisuje przyszłe kroki: szkic demo, publikacja po akceptacji, spersonalizowana wiadomość, klasyfikacja odpowiedzi, Telegram, wycena i finalna strona po akceptacji. Tabela `automation_events` zapisuje jedynie identyfikator rekordu, typ i czas z `state: blocked`. Nie ma workerów, SDK, tokenów, adresów botów ani wysyłki. Sam wysoki wynik lub zdarzenie nie uruchamia żadnej akcji. Obecne etapy należy traktować jako kontrakt do dalszej implementacji.

## Eksporty, testy i ograniczenia

CSV ma UTF-8 z BOM, daty, źródła i uzasadnienia w polach JSON; komórki rozpoczynające się od `=`, `+`, `-`, `@` są zabezpieczone przed interpretacją jako formuła. JSON zachowuje pełną ocenę, pochodzenie i workflow panelu. Eksporty są tworzone jako nowe pliki, bez nadpisywania wcześniejszych danych.

```sh
python -m unittest discover -s prospect-finder/tests -v
node prospect-finder/tests/panel.test.mjs
npm --prefix demo-generator test
```

Nie dodano live discovery, automatycznego audytu witryn, AI, publikacji rzeczywistych firm, wysyłki, płatnych usług ani nowego hostingu. Koszt bibliotek/API: **0 zł**. Korzystanie z istniejącego komputera/hostingu pozostaje według jego warunków. Przed podłączeniem prawdziwego źródła i komunikacji należy osobno zweryfikować dane, warunki źródła i podstawę kontaktu. Zatwierdzona lista 30 branż i konfiguracja udostępnienia panelu na iPadzie pozostają do potwierdzenia.
