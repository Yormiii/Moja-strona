# AUDYT WEBFORGE — analiza projektu i wspólny dziennik pracy

- Repozytorium: [Yormiii/Moja-strona](https://github.com/Yormiii/Moja-strona).
- Analizowana gałąź: `main`.
- Commit będący podstawą audytu: `7a53aad3a3252cdeaafd6783eea392644391329e` (`7a53aad`), z 19 lipca 2026 r., komunikat „Add files via upload”.
- Data analizy i utworzenia dziennika: 27 października 2026 r.
- Status audytu bazowego: audyt i plan; w chwili jego wykonania poprawki, generator oraz migracja hostingu nie były wdrożone. Aktualny stan realizacji opisuje dziennik poniżej.
- Zakres: odczyt wszystkich plików tekstowych, pełnej struktury repozytorium, konfiguracji formularzy i historii wdrożeń; porównanie demonstracji i sprawdzenie lokalnych odnośników.
- Nie przeprowadzono testowego wysłania formularzy. Nie potwierdzono bieżącego DNS ani działania domeny w przeglądarce. Analiza kodu nie zastępuje testów wizualnych i testu doręczenia poczty.

## Zasady wspólnego dziennika i zakres upoważnienia

Na polecenie właściciela projektu ten plik jest wspólnym dziennikiem pracy nad WebForge.

1. Po każdym kolejnym zadaniu aktualizować ten dokument o wykonane działania, wyniki, napotkane problemy i następne kroki.
2. Zachować ustalenia audytu oraz historię; przy zmianie stanu oznaczać, co rozwiązano, zamiast usuwać kontekst.
3. Oddzielać ustalone fakty, nieweryfikowane informacje, rekomendacje i faktycznie wykonane prace.
4. Nie zmieniać innych plików projektu bez zgody użytkownika. Zgoda na prowadzenie dziennika nie jest zgodą na wdrażanie opisanych rekomendacji.
5. Nie dodawać do publicznego repozytorium sekretów, prywatnych danych potencjalnych klientów, wewnętrznych notatek handlowych ani danych dostępowych.
6. Niniejsze zadanie upoważnia do utworzenia i opublikowania wyłącznie `AUDYT_WEBFORGE.md`, najlepiej bezpośrednio na `main`.
7. Aktualizacja zakresu — Zadanie 1 (2026-10-27): użytkownik zezwolił na dodanie generatora, przykładów, instrukcji i testów oraz aktualizację audytu wyłącznie na `feature/demo-generator`. Nie zmieniać `main`, istniejących stron, formularzy ani plików produkcyjnych. Nie publikować na domenie, nie konfigurować płatnych usług, nie tworzyć PR i nie scalać gałęzi. To nowsze polecenie zastępuje zakres z punktu 6 dla tego zadania.

## Główna rekomendacja

**Najprostsze rozwiązanie to generator statycznych stron: obecny szablon HTML + dane firmy w JSON → gotowe demo pod osobnym adresem.** Nie potrzeba WordPressa, bazy danych ani płatnego kreatora. Hosting generatora i demonstracji może kosztować **0 zł miesięcznie** przy niewielkiej skali.

Rekomendowany zestaw: **obecny wygląd + wspólny szablon + JSON + mały generator Node.js + Cloudflare Pages Free**. Pozwala zacząć z dodatkowymi kosztami infrastruktury bliskimi zeru, a wygodny panel i AI dołożyć dopiero wtedy, gdy liczba demonstracji uzasadni ich budowę.

W trakcie samego audytu niczego nie zmieniano ani nie publikowano. Późniejsze utworzenie tego dokumentu jest osobnym, wyraźnie autoryzowanym zadaniem.

## 1. Struktura projektu i technologie

Repozytorium w analizowanym commicie zawiera 16 plików, wszystkie w głównym katalogu. Liczba ta nie obejmuje dodawanego później pliku audytu.

| Pliki | Rola |
|---|---|
| `index.html` | Strona główna WebForge |
| Osiem plików `demo-*.html` | Demonstracje branżowe |
| `dziekujemy.html` | Potwierdzenie po wysłaniu formularza |
| `polityka-prywatnosci-gotowa.html` | Polityka prywatności |
| `favicon.png`, `webforge-logo.png` | Grafiki |
| `CNAME` | Domena `webforge.com.pl` |
| `robots.txt`, `sitemap.xml` | Konfiguracja indeksowania |

### Technologie i działanie

- Zwykły **HTML i CSS**, ze stylami wewnątrz każdego pliku.
- Niewielki JavaScript na stronie głównej: animacje podczas przewijania przez `IntersectionObserver`.
- Responsywność przez CSS Grid, Flexbox i media queries.
- Formularze obsługuje zewnętrzny **FormSubmit**.
- Brak Reacta, frameworka, backendu, bazy danych, zależności npm oraz własnego procesu budowania.
- W analizowanym drzewie nie ma własnych plików workflow w `.github/workflows`.
- `robots.txt` dopuszcza indeksowanie całej witryny i wskazuje mapę strony.
- `sitemap.xml` zawiera wyłącznie adres strony głównej.
- Strona podziękowania ma `noindex`; obecne demonstracje nie mają takiego oznaczenia.

To lekki projekt, który dobrze nadaje się do automatycznego generowania kolejnych stron. Główna trudność przy rozbudowie to kopiowanie tego samego kodu między plikami.

Źródło: [pliki projektu](https://github.com/Yormiii/Moja-strona/tree/main).

## 2. Strony demonstracyjne i możliwość użycia ich jako szablonów

**Na stronie głównej pokazane są trzy dema, ale w repozytorium jest osiem.**

### Trzy demonstracje pokazane w portfolio

| Demo | Plik | Charakterystyka |
|---|---|---|
| AutoPro Serwis | `demo-mechanik.html` | Warsztat, pomarańczowe akcenty, cztery usługi |
| North Cut Barber | `demo-barber.html` | Barber, złote akcenty, cztery usługi |
| Studio Lumière | `demo-stylistka.html` | Beauty, różowe akcenty, cztery usługi |

### Wszystkie warianty branżowe

| Plik | Nazwa demonstracyjna | Branża | Przykładowe usługi |
|---|---|---|---|
| `demo-mechanik.html` | AutoPro Serwis | Warsztat samochodowy | Diagnostyka komputerowa, wymiana oleju i filtrów, hamulce i zawieszenie, klimatyzacja |
| `demo-barber.html` | North Cut Barber | Barbershop | Strzyżenie męskie, broda i kontur, pakiet włosy + broda, golenie brzytwą |
| `demo-stylistka.html` | Studio Lumière | Beauty | Stylizacja paznokci, brwi i rzęsy, makijaż okazjonalny, pakiety ślubne |
| `demo-elektryk.html` | VoltPro | Elektryk | Nowe instalacje, pomiary elektryczne, modernizacje rozdzielni, usuwanie usterek |
| `demo-hydraulik.html` | HydroFix 24 | Usługi hydrauliczne | Usuwanie awarii, montaż armatury, instalacje wodne, udrażnianie odpływów |
| `demo-kancelaria.html` | Kancelaria Lexum | Usługi prawne | Prawo cywilne, obsługa firm, umowy i dokumenty, konsultacje prawne |
| `demo-restauracja.html` | Bistro Verde | Restauracja | Menu sezonowe, lunch dnia, przyjęcia rodzinne, catering |
| `demo-trener.html` | Forma Studio | Trener personalny | Trening personalny, plan treningowy, analiza postępów, trening online |

Pięć pozostałych wariantów nie jest obecnie podlinkowanych z portfolio.

### Wspólna konstrukcja

Wszystkie osiem demonstracji ma wspólny układ:

1. Pasek powrotu do WebForge.
2. Nawigacja i sekcja otwierająca.
3. Cztery usługi.
4. Sekcje „Dlaczego my” oraz „Jak to działa”.
5. Przykładowa galeria.
6. Sekcja kontaktowa i stopka.

Porównanie kodu wykazało, że **CSS wszystkich demonstracji jest identyczny poza wartościami zmiennych kolorystycznych**. Różnice dotyczą głównie nazwy firmy, branży, nagłówka, usług i krótkich opisów.

### Co rzeczywiście działa

- Nawigacja przewija stronę do sekcji.
- Układ dopasowuje się do szerokości ekranu.
- Link powrotu prowadzi do portfolio WebForge.
- Końcowy przycisk prowadzi do formularza na stronie WebForge.
- Demonstracje są samodzielnymi stronami HTML, bez skryptów i formularzy.
- Statyczna kontrola odnośników lokalnych w ośmiu demonstracjach nie wykazała brakujących plików przy obecnym położeniu stron.

### Co jest tylko demonstracją

- Nie ma systemu rezerwacji, kalendarza ani formularzy w samych demach.
- „Galerie” to kolorowe bloki z napisami, bez zdjęć; demonstracje nie zawierają elementów `img`.
- Przyciski „Zarezerwuj termin” lub „Umów wizytę” przewijają do sekcji kontaktowej.
- Brakuje rzeczywistych danych kontaktowych prezentowanej firmy.
- Końcowy przycisk kieruje do WebForge, a nie do rzeczywistej firmy.

Opisy portfolio obiecują miejscami więcej niż realizują demonstracje: np. mapę, telefon, cennik czy formularz rezerwacji. Warto ujednolicić opisy z faktyczną funkcjonalnością.

### Przydatność jako szablony

**Można wykorzystać je jako szablony.** Najlepiej wyodrębnić jeden wspólny szablon i osiem zestawów danych branżowych. Na start wystarczy personalizacja nazwy firmy, miasta, kolorów, usług, tekstów, logo i zdjęć.

Źródła: [demo warsztatu](https://github.com/Yormiii/Moja-strona/blob/main/demo-mechanik.html), [demo barbera](https://github.com/Yormiii/Moja-strona/blob/main/demo-barber.html), [demo beauty](https://github.com/Yormiii/Moja-strona/blob/main/demo-stylistka.html).

## 3. Formularz kontaktowy i formularz opinii

Na stronie głównej są **dwa formularze**: zapytania ofertowego i opinii. Oba wysyłają zwykły HTTP POST do:

`https://formsubmit.co/kontakt@webforge.com.pl`

Przepływ:

**Użytkownik → FormSubmit → e-mail WebForge → strona podziękowania.**

### Formularz ofertowy

Formularz `quoteForm` przekazuje:

- imię lub nazwę firmy,
- opcjonalny telefon,
- e-mail,
- rodzaj strony,
- budżet,
- opis projektu,
- zaznaczenie zgody na kontakt.

Pola imienia/nazwy firmy, e-maila, opisu projektu i zgody są wymagane w HTML. Telefon jest opcjonalny.

Konfiguracja obejmuje:

- pole pułapkę `_honey`,
- włączoną CAPTCHA: `_captcha=true`,
- temat „Nowe zapytanie ze strony WebForge”,
- tabelaryczny format e-maila: `_template=table`,
- przekierowanie `_next` na `https://webforge.com.pl/dziekujemy.html`.

Formularz działa bez własnego JavaScriptu i backendu.

### Formularz opinii

Formularz `reviewForm` przekazuje autora, e-mail do weryfikacji, ocenę i treść opinii. Używa tego samego adresu FormSubmit, pola pułapki, CAPTCHA i formatu tabeli. Ma osobny temat „Nowa opinia o WebForge” oraz przekierowanie na `dziekujemy.html?typ=opinia`.

**Wysyła wiadomość e-mail — nie publikuje opinii automatycznie.** Strona opisuje ręczną weryfikację i zgodę autora przed publikacją. W repozytorium nie ma systemu zapisu opinii ani panelu administracyjnego.

### Aktywacja i ograniczenia weryfikacji

FormSubmit wymaga potwierdzenia adresu odbiorcy podczas pierwszego uruchomienia. **Z repozytorium nie można potwierdzić, czy aktywacja została wykonana i czy wiadomości faktycznie docierają.**

Nie wysyłano formularzy testowych. Nie zweryfikowano dostępu do skrzynki `kontakt@webforge.com.pl`, filtrów antyspamowych ani końcowego doręczenia.

`dziekujemy.html` jest statyczną stroną. Jej otwarcie samo w sobie nie potwierdza doręczenia wiadomości do skrzynki.

### Znaleziony błąd

**Formularz i stopka wskazują `polityka-prywatnosci.html`, a istniejący plik nazywa się `polityka-prywatnosci-gotowa.html`.** W analizowanym repozytorium brakuje pliku docelowego wskazanego odnośnikiem.

### Rekomendacja

Najtaniej pozostawić FormSubmit, poprawić odnośnik i później wykonać kontrolowany test obu formularzy. Zmiana kodu i testowe wysyłki nie zostały wykonane w ramach audytu.

Źródła: [kod formularzy](https://github.com/Yormiii/Moja-strona/blob/main/index.html), [istniejąca polityka prywatności](https://github.com/Yormiii/Moja-strona/blob/main/polityka-prywatnosci-gotowa.html), [strona podziękowania](https://github.com/Yormiii/Moja-strona/blob/main/dziekujemy.html), [dokumentacja FormSubmit](https://formsubmit.co/).

## 4. Wdrożenie i hosting

### Potwierdzone ustalenia

**Potwierdzono wdrażanie przez GitHub Pages.**

Dowody:

- `CNAME` zawiera `webforge.com.pl`.
- Ostatni znaleziony przebieg `pages build and deployment` zakończył się sukcesem 19 lipca 2026 r.
- Wdrożenie dotyczy commita `7a53aad3a3252cdeaafd6783eea392644391329e`, który był również aktualnym commitem `main` podczas audytu.
- Przebieg o identyfikatorze `29697014262` rozpoczął się o 17:32:03 UTC i zakończył o 17:33:03 UTC.
- Ścieżka `dynamic/pages/pages-build-deployment` wskazuje na wbudowany mechanizm GitHub Pages; własnego workflow w repozytorium nie ma.
- Gałąź przebiegu to `main`; witryna jest przechowywana jako pliki w katalogu głównym.

Źródła: [udane wdrożenie](https://github.com/Yormiii/Moja-strona/actions/runs/29697014262), [konfiguracja domeny](https://github.com/Yormiii/Moja-strona/blob/main/CNAME).

### Czego nie potwierdzono

To potwierdza platformę ostatniego wdrożenia. **Nie potwierdzono bieżącej konfiguracji DNS ani dostępności domeny** — narzędzie przeglądania nie zdołało otworzyć strony głównej ani sprawdzanych adresów demonstracji i polityki. Nie jest to wystarczający dowód, że strona nie działa.

Nie można też ustalić z tych plików dostawcy poczty ani rejestratora domeny. Odczyt kolekcji wdrożeń przez użyte narzędzie GitHub był niedostępny; ustalenie dotyczące hostingu oparto na dostępnym przebiegu GitHub Actions, a nie na tej kolekcji.

### Rekomendacja hostingowa

Przy rozwoju systemu demonstracji rekomendowany jest **Cloudflare Pages**.

GitHub opisuje ograniczenia używania Pages do prowadzenia biznesu i obsługi transakcji komercyjnych, dlatego nie należy opierać na nim docelowego systemu sprzedażowych demonstracji. To rekomendacja dotycząca dalszej architektury, a nie potwierdzenie naruszenia zasad przez obecną witrynę.

Źródło: [zasady GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## 5. Proponowany system automatycznego generowania indywidualnych demo

### Zakres najprostszej wersji

Rekomendowany jest **jeden generator uruchamiany podczas budowania strony**, wykorzystujący obecne HTML i CSS.

Przebieg:

**Wpisujesz dane firmy → wybierasz branżę → generator tworzy HTML → hosting publikuje demo → otrzymujesz link.**

Przykładowy adres:

`https://demo.webforge.com.pl/autoserwis-kowalski-a7k2/`

Jest to adres planowany, nie istniejące wdrożenie potwierdzone podczas audytu.

Jedna subdomena i jeden projekt hostingowy obsłużą wiele demonstracji. Nie potrzeba osobnej domeny ani oddzielnego wdrożenia dla każdego klienta.

### Proponowana struktura nowych plików

```text
templates/demo.html         wspólny szablon
data/industries.json        warianty branżowe
data/clients/*.json         dane poszczególnych firm
scripts/build.mjs          generator w Node.js
dist/                      wynik gotowy do publikacji
```

To planowane pliki; ich utworzenie wymaga osobnej zgody użytkownika.

### Obowiązki generatora

Generator powinien:

- wstawiać nazwę, miasto, usługi, kolory i materiały firmy;
- bezpiecznie kodować treści oraz sprawdzać adresy linków;
- tworzyć unikalny adres każdej demonstracji;
- poprawnie ustawiać odnośniki do WebForge — obecne względne `index.html#kontakt` wymaga zmiany przy zagnieżdżonych adresach;
- dodawać oznaczenie „Propozycja strony przygotowana przez WebForge”;
- ustawiać `noindex` i pomijać indywidualne dema w sitemapie;
- umożliwiać wyłączenie demonstracji przez zmianę jej statusu w danych.

### Dane i prywatność

**`noindex` ogranicza indeksowanie, ale nie zapewnia prywatności.**

Ponieważ obecne repozytorium jest publiczne, nie należy umieszczać w nim wewnętrznych notatek, budżetów ani prywatnych danych kontaktowych potencjalnych klientów. Sam trudny do odgadnięcia adres także nie zastępuje kontroli dostępu.

Na początku dane można dodawać przez edytor GitHub. Automatyczne będzie tworzenie i publikowanie stron; zbieranie informacji o firmach pozostanie ręczne. To najprostszy zakres, który daje realną oszczędność pracy.

### Rola AI

AI można dodać później wyłącznie do przygotowywania propozycji tekstów. Nie powinno samodzielnie wymyślać opinii, kwalifikacji, cen czy doświadczenia firmy. Do pierwszej wersji API AI nie jest potrzebne.

### Hosting generatora i demonstracji

Najpierw uruchomić osobny projekt demonstracji na `demo.webforge.com.pl`. Migrację głównej witryny przeprowadzić osobno po sprawdzeniu podglądu.

Cloudflare obsługuje zwykły HTML oraz automatyczne budowanie po zmianach w GitHub. Generator ma tworzyć katalog `dist/`, a hosting publikować jego zawartość. Nie jest potrzebny działający stale serwer generatora ani baza danych.

Źródła: [obsługa HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/), [integracja GitHub](https://developers.cloudflare.com/pages/configuration/git-integration/).

## 6. Konkretny plan wdrożenia

| Etap | Zakres | Szacowany czas |
|---|---|---:|
| 1. Uporządkowanie | Link polityki, opisy portfolio, sprawdzenie formularzy | 1–2 godz. |
| 2. Szablon | Wspólny HTML/CSS i osiem wariantów branżowych | 3–5 godz. |
| 3. Generator | Dane JSON, walidacja, adresy, zdjęcia, status demonstracji | 4–6 godz. |
| 4. Hosting | Podłączenie repozytorium do Cloudflare Pages, budowanie `dist/`, subdomena demo | 1–3 godz. |
| 5. Weryfikacja | Trzy przykładowe firmy, widok mobilny, linki, indeksowanie i formularze | 2–4 godz. |

**Łącznie: około 11–20 godzin pracy**, zależnie od jakości materiałów i zakresu personalizacji. To szacunek, nie wycena wykonawcy.

Plan jest propozycją. Żaden z tych etapów nie został wykonany w ramach audytu ani samego zapisania dokumentacji.

## 7. Orientacyjne koszty

Dla kilkudziesięciu lub kilkuset lekkich demonstracji:

| Element | Koszt |
|---|---:|
| Generator Node.js | 0 zł opłat za oprogramowanie |
| Cloudflare Pages Free i HTTPS | 0 zł/mies. w limitach planu |
| FormSubmit | 0 zł według oferty sprawdzonej podczas audytu |
| Baza danych | Niepotrzebna |
| API AI | 0 zł — niepotrzebne w pierwszej wersji |
| Subdomena `demo.webforge.com.pl` | Zwykle bez dodatkowej opłaty |
| Odnowienie obecnej domeny | Według obecnego rejestratora; budżetowo ok. 60–150 zł/rok |
| Obecna skrzynka e-mail | Według obecnego dostawcy; koszt nieustalony |

Cloudflare Pages Free ma według dokumentacji sprawdzonej podczas audytu limit **500 buildów miesięcznie i 20 000 plików na stronę**. Jedno budowanie może wygenerować wszystkie dema naraz. Przy większych paczkach warto dodawać wiele firm w jednej zmianie.

Źródła: [limity Cloudflare](https://developers.cloudflare.com/pages/platform/limits/), [Cloudflare Pages](https://www.cloudflare.com/products/pages/), [FormSubmit](https://formsubmit.co/).

Przy zleceniu wdrożenia i przykładowej stawce 100–200 zł/h jednorazowy koszt wyniósłby orientacyjnie **1100–4000 zł**, bez zakupu zdjęć, pisania indywidualnych tekstów i ewentualnego VAT.

Kwota 0 zł/mies. dotyczy dodatkowej infrastruktury najprostszej wersji w darmowych limitach. Nie obejmuje pracy człowieka, obecnej poczty, odnowienia domeny ani płatnych materiałów. Widełki domeny są założeniem budżetowym, a nie ustaloną fakturą lub ofertą obecnego rejestratora. Ceny i limity należy ponownie sprawdzić przed wdrożeniem.

## 8. Rejestr problemów i otwartych kwestii

| ID | Ustalenie lub problem | Status | Zalecane następne działanie |
|---|---|---|---|
| P-01 | Linki do `polityka-prywatnosci.html` nie odpowiadają istniejącej nazwie pliku | Otwarte | Po zgodzie poprawić ścieżkę albo nazwę pliku i sprawdzić oba odnośniki |
| P-02 | Opisy trzech pozycji portfolio wymieniają funkcje nieobecne w demonstracjach | Otwarte | Ujednolicić opisy z demonstracjami albo osobno uzgodnić dodanie funkcji |
| P-03 | Powielony HTML/CSS w ośmiu demonstracjach | Otwarte | Wydzielić wspólny szablon i dane branżowe |
| P-04 | Brak potwierdzenia aktywacji FormSubmit i doręczenia poczty | Niezweryfikowane | Kontrolowany test formularza zapytania i opinii oraz sprawdzenie skrzynki |
| P-05 | Otwarcie strony podziękowania nie jest dowodem doręczenia e-maila | Ograniczenie obecnej konstrukcji | Weryfikować dostarczenie po stronie odbiorcy |
| P-06 | Nie potwierdzono aktualnego DNS i dostępności domeny | Niezweryfikowane | Sprawdzić DNS, HTTPS i odpowiedzi serwera; błąd narzędzia nie dowodzi awarii |
| P-07 | Rejestrator domeny, dostawca poczty i rzeczywiste koszty są nieznane | Niezweryfikowane | Ustalić na podstawie paneli lub dokumentów właściciela |
| P-08 | Względne powroty do WebForge przestaną wskazywać właściwe miejsce po przeniesieniu demo do podkatalogów/subdomeny | Do uwzględnienia w generatorze | Stosować poprawne docelowe adresy WebForge |
| P-09 | Indywidualne demo i dane w publicznym repozytorium nie są prywatne | Wymóg projektowy | Ograniczyć dane publikowane; `noindex` nie traktować jako zabezpieczenia |
| P-10 | GitHub Pages ma ograniczenia zastosowań biznesowych | Rekomendacja architektoniczna | Docelowy system demonstracji oprzeć na Cloudflare Pages |
| P-11 | Brak generatora, panelu i integracji AI | Planowane, niewdrożone | Zacząć od generatora JSON → HTML; panel i AI rozważyć później |
| P-12 | Pięć dodatkowych wariantów nie jest pokazanych w portfolio | Ustalenie | Można wykorzystać w generatorze; ewentualna zmiana portfolio wymaga zgody |

## 9. Dziennik pracy

### 2026-10-27 — sprawdzenie dostępu do repozytorium

**Wykonane działania:**

- Odczytano metadane repozytorium `Yormiii/Moja-strona`.
- Potwierdzono dostęp do gałęzi `main`, listy plików i fragmentu `index.html`.
- Potwierdzono, że odczytany plik dotyczy projektu WebForge.

**Wyniki:** dostęp do repozytorium i odczyt plików działają.

**Problemy:** nie napotkano przeszkód w odczycie przez połączenie GitHub.

**Następne kroki:** szczegółowa analiza projektu zgodnie z kolejnym poleceniem użytkownika.

**Zakres zmian:** brak zmian w repozytorium.

### 2026-10-27 — szczegółowy audyt gałęzi main

**Wykonane działania:**

- Odczytano pełne drzewo `main` i wszystkie pliki tekstowe.
- Przeanalizowano stronę główną, osiem demonstracji, oba formularze, politykę prywatności, stronę podziękowania, `CNAME`, `robots.txt` i `sitemap.xml`.
- Porównano CSS demonstracji; potwierdzono wspólny kod poza zmiennymi kolorystycznymi.
- Sprawdzono odnośniki lokalne i wykryto brak pliku wskazywanego przez link polityki prywatności.
- Odczytano historię GitHub Actions i znaleziono udane wdrożenie aktualnego commita przez GitHub Pages.
- Podjęto próbę odczytu domeny narzędziem przeglądania.
- Sprawdzono oficjalne materiały FormSubmit, Cloudflare Pages i ograniczenia GitHub Pages.
- Przedstawiono plan generatora, plan wdrożenia oraz orientacyjne koszty.

**Wyniki:** pełne ustalenia, rekomendacje i plan znajdują się w sekcjach 1–8 tego dokumentu.

**Problemy i ograniczenia:**

- Narzędzie przeglądania nie uzyskało dostępu do domeny; nie ustalono przyczyny i nie stwierdzono na tej podstawie awarii witryny.
- Endpoint kolekcji wdrożeń nie był obsługiwany przez użyte narzędzie; dowód wdrożenia uzyskano z GitHub Actions.
- Nie wysłano formularzy i nie potwierdzono aktywacji ani końcowego doręczenia wiadomości.
- Nie ustalono dostawcy poczty, rejestratora domeny ani rzeczywistych opłat.

**Następne kroki:** zachowanie audytu w repozytorium; wdrożenie poprawek lub generatora dopiero w zakresie osobno zatwierdzonym przez użytkownika.

**Zakres zmian:** sam audyt był wyłącznie odczytem; nie zmieniono ani nie opublikowano plików projektu.

### 2026-10-27 — zapis audytu i ustanowienie wspólnego dziennika

**Polecenie użytkownika:** zapisać pełną przedstawioną analizę do `AUDYT_WEBFORGE.md`, utworzyć commit i opublikować go na GitHubie, najlepiej na `main`. Od tej pory prowadzić w tym pliku dziennik po każdym zadaniu. Nie zmieniać innych plików bez zgody.

**Wykonane działania objęte tym wpisem:**

- Ponownie odczytano drzewo gałęzi `main`; przed dodaniem dokumentu nadal wskazywało commit `7a53aad3a3252cdeaafd6783eea392644391329e`.
- Potwierdzono brak istniejącego `AUDYT_WEBFORGE.md`.
- Przygotowano niniejszy dokument zawierający całą przedstawioną analizę, wszystkie problemy, rekomendacje, plan automatyzacji, etapy wdrożenia i szacunkowe koszty.
- Dodano zasady prowadzenia wspólnego dziennika, rejestr otwartych kwestii i historię dotychczasowych zadań.

**Wynik zapisu:** przygotowano pełną treść dokumentu i zapisano ją lokalnie jako `/workspace/AUDYT_WEBFORGE.md`. Próba utworzenia pliku i commita bezpośrednio na `main` przez API GitHub została odrzucona. Nie utworzono commita ani nie opublikowano pliku w repozytorium. Żaden istniejący plik projektu nie został zmieniony.

**Problemy:**

- Na etapie przygotowania dokumentu nie stwierdzono konfliktu z istniejącym plikiem ani zmiany bazowego commita.
- Integracja GitHub zwróciła przy tworzeniu pliku błąd `403: Resource not accessible by integration`.
- Sprawdzono środowisko zgodnie z instrukcjami `cloud-environment-runtime`; nie wykazano skonfigurowanych dodatkowych poświadczeń zapisu.
- `gh auth status` zgłosiło nieważny token `GH_TOKEN`.
- Próba pobrania publicznego repozytorium przez Git zakończyła się brakiem połączenia z serwerem proxy na porcie 8080.
- Z powodu tych przeszkód nie było możliwe utworzenie i opublikowanie commita na GitHubie. To blokada techniczna, nie brak zgody użytkownika.

**Następne kroki:**

- Przywrócić działające połączenie GitHub z prawem zapisu zawartości do repozytorium `Yormiii/Moja-strona`.
- Po przywróceniu dostępu ponownie sprawdzić aktualną gałąź i ewentualne istnienie dokumentu, utworzyć commit obejmujący wyłącznie ten plik i opublikować go na `main`, jeśli zasady gałęzi na to pozwalają.
- Po publikacji zweryfikować treść pliku oraz potwierdzić, że commit obejmuje wyłącznie ten dokument.
- Po każdym następnym zadaniu dopisywać działania, wyniki, problemy i następne kroki.
- Oczekiwać kolejnego zadania użytkownika; poprawki kodu, generator, migracja i zmiany DNS pozostają niewdrożone i wymagają odrębnej zgody.

**Zakres zmian:** wyłącznie `AUDYT_WEBFORGE.md`; bez zmian HTML, CSS, formularzy, konfiguracji hostingu i domeny. Commit dokumentacji na `main` może uruchomić istniejący automatyczny proces GitHub Pages; nie jest to wdrożenie proponowanego generatora ani migracja.


### 2026-10-27 — Zadanie 1: pierwsza wersja generatora demonstracji

**Zgoda i zakres:** użytkownik zlecił generator, fikcyjny przykład, instrukcję i testy oraz aktualizację dziennika na osobnej gałęzi `feature/demo-generator`. Zabronił zmian `main`, istniejących stron, formularzy i innych plików produkcyjnych, wdrażania na domenę, płatnych usług, tworzenia PR i scalania.

**Stan początkowy i odczyt audytu:**

- Najpierw przeczytano lokalny audyt, następnie jego aktualną kopię z GitHub.
- Na GitHubie audyt jest już obecny: aktualny snapshot `main` to `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`. Historyczny wpis o wcześniejszym nieudanym zapisie pozostawiono jako historię; opisuje poprzednią próbę, nie aktualny brak dokumentu.
- Odczytano wszystkie 17 plików tego snapshotu przez integrację GitHub. Lokalną bazę odtworzono z oryginalnych obiektów, sprawdzając SHA każdego pliku, drzewa i podpisanego commita. To płytka lokalna kopia Git, z tym samym commitem bazowym co GitHub.
- Utworzono lokalną gałąź `feature/demo-generator`; nie tworzono ani nie zmieniano lokalnej gałęzi `main`.

**Wykonane działania:**

- Dodano wyłącznie nowy katalog `demo-generator/` i zaktualizowano niniejszy audyt.
- `templates/demo.html`: wspólny układ i CSS bazujące na ośmiu istniejących demonstracjach; źródła produkcyjne pozostały nienaruszone.
- `data/industries.json`: etykiety, kolory i CTA ośmiu branż: mechanik, barber, stylistka, elektryk, hydraulik, kancelaria, restauracja i trener. Każdy profil wskazuje plik źródłowy.
- `generate.mjs`: generator Node.js bez zależności zewnętrznych. Czyta JSON z nazwą, branżą, miastem, usługami, opisem, kolorami i kontaktem; tworzy samodzielny HTML w `demo-generator/generated/<slug>/index.html`.
- Obsłużono 1–12 usług jako tekst lub obiekty z opisami, dane telefonu/e-maila/WWW/adresu, opcjonalne kolory branżowe, jawny lub automatyczny slug z obsługą polskich znaków i stabilnym skrótem.
- Dodano walidację wymaganych i nieznanych pól, kolorów, kontaktów i bezpiecznych adresów HTTP/HTTPS; kodowanie treści HTML; ochronę przed przejściem poza katalog wyników i symlinkami. Nadpisanie wymaga jawnego `--force`.
- Gotowe demo ma widoczne oznaczenie propozycji WebForge, `noindex, nofollow`, bezwzględne odnośniki do WebForge i prawidłowe kotwice sekcji. Nie zawiera skryptów, formularzy, systemu rezerwacji ani fikcyjnych opinii czy kwalifikacji.
- `examples/firma-testowa.json`: fikcyjna firma „Serwis Orbita TEST — firma fikcyjna”, Łódź, trzy usługi, własne kolory i wyłącznie fikcyjne dane kontaktowe (domeny `.invalid`, zerowy telefon).
- Wygenerowano i dołączono `generated/serwis-orbita-test/index.html`.
- Dodano `README.md` z uruchamianiem, schematem danych, listą branż, instrukcją podglądu, zakresem i ograniczeniami, oraz `package.json` ze skryptami bez instalowania pakietów.
- Dodano 13 testów opartych na wbudowanym `node:test`.

**Uruchamianie z katalogu głównego repozytorium:**

```sh
node demo-generator/generate.mjs demo-generator/examples/firma-testowa.json --force
node --test demo-generator/test/*.test.mjs
```

Do szczegółowego raportu wszystkich przypadków można również uruchomić `node demo-generator/test/generator.test.mjs`. W tym środowisku tryb `--test` raportował pojedynczy plik testowy jako zbiorczy wynik; bezpośrednie uruchomienie potwierdziło wszystkie 13 przypadków.

**Wyniki weryfikacji:**

- Node.js 24.19.0; deklarowane minimum projektu: Node.js 20. Nie wykonywano osobnego przebiegu na Node.js 20.
- **13/13 testów przeszło, 0 błędów.** Sprawdzono: zgodność ośmiu profili z demonstracjami źródłowymi, personalizację, kontakty, noindex i oznaczenie demo, kotwice i niezależność od lokalnych zasobów, brak formularzy/skryptów, XSS i jednokrotne podstawianie znaczników, błędne dane, protokoły URL, polskie znaki i rozróżnianie slugów, zapis i jawne odświeżanie, brak plików przy błędzie, symlinki, błędy CLI, generowanie z innego katalogu i odtwarzalność przykładu.
- `npm --prefix demo-generator test` oraz kontrola składni `node --check demo-generator/generate.mjs` zakończyły się powodzeniem.
- Wygenerowany HTML jest odtwarzalny z JSON; test porównuje go z dołączonym wynikiem.
- Kontrola Git potwierdziła brak zmian w istniejących plikach produkcyjnych. Zmiany obejmują tylko `AUDYT_WEBFORGE.md` i osiem nowych plików w `demo-generator/`.
- Próba podglądu mobilnego i desktopowego przez Playwright nie zakończyła się renderowaniem: brak przeglądarki w cache, a systemowy Chromium przerwał start z `setsockopt: Operation not permitted` / SIGTRAP. Nie potwierdzono wizualnie wyglądu ani braku poziomego przewijania. Nie przedstawiać tej próby jako zaliczonego testu wizualnego.

**GitHub, commit i ograniczenia:**

- Próba utworzenia zdalnej gałęzi `feature/demo-generator` z aktualnego `main` została odrzucona: `403 Resource not accessible by integration`. Zdalna gałąź nie została utworzona.
- Zwykłe klonowanie Git również nie zadziałało: brak połączenia z proxy na porcie 8080. Nie obchodzono proxy i nie zmieniano konfiguracji poświadczeń.
- Przygotowano lokalny commit na `feature/demo-generator` oraz eksport zmian jako ZIP i patch do zastosowania po przywróceniu zapisu. SHA lokalnego commita odczytać z `git log -1`; nie wpisuje się własnego SHA do treści tego samego commita.
- Nie wysłano zmian do GitHub, nie utworzono PR i nie scalono gałęzi. Brak działającego linku do zdalnej gałęzi.
- Nie uruchomiono wdrożenia, nie modyfikowano domeny, DNS, hostingu, formularzy, `CNAME`, sitemap ani produkcyjnych demonstracji. Nie skonfigurowano płatnych usług. Dodatkowy koszt wykonania generatora w tej wersji: brak opłat za API lub infrastrukturę.

**Stan wcześniejszych rekomendacji:**

- P-03: wspólny szablon i dane wyodrębniono dla nowego generatora; istniejące osiem stron zachowano bez refaktoryzacji.
- P-08: nowe demo używa bezwzględnych odnośników do WebForge.
- P-09: dodano oznaczenie i noindex; dane przykładu fikcyjne. Noindex nadal nie zapewnia prywatności.
- P-11: generator v0.1 działa lokalnie; panel, AI i automatyczne wdrożenie nadal nie są zaimplementowane.
- P-01, P-02 oraz pozostałe niezweryfikowane kwestie produkcyjne pozostają otwarte; nie poprawiano ich w tym zadaniu.

**Następne kroki:**

1. Przywrócić integracji GitHub prawo zapisu i utworzyć zdalne `feature/demo-generator`, publikując wyłącznie przygotowane zmiany (bez PR i bez modyfikacji `main`). Przed publikacją sprawdzić aktualny stan gałęzi i ewentualne równoległe zmiany; nie wymuszać nadpisania.
2. Sprawdzić wygenerowany przykład wizualnie w działającej przeglądarce na telefonie i komputerze oraz uzgodnić wygląd i kontrast.
3. W osobnym zadaniu rozważyć obsługę paczki wielu firm, statusów aktywne/wyłączone, zdjęć i wygodnego wprowadzania danych.
4. Hosting na osobnej subdomenie i automatyczne wdrożenie pozostają osobnym etapem wymagającym zgody.
5. Po następnym zadaniu ponownie uzupełnić dziennik; historyczne analizy zachować.

### 2026-10-27 — ponowienie publikacji po aktualizacji uprawnień GitHub

**Polecenie:** opublikować gotowy generator i audyt na `feature/demo-generator`, bez zmian `main` i bez Pull Requesta.

**Wykonane działania:**

- Odczytano dziennik, stan lokalnej gałęzi i commit generatora `0d154e03f10dcb0d8def6ad88aa0b54f5dbc996d`.
- Sprawdzono aktualny `main`: nadal `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`. Nie było równoległych zmian wymagających scalenia.
- Sprawdzono listę gałęzi: `feature/demo-generator` jeszcze nie istniała.
- Po aktualizacji uprawnień udało się utworzyć zdalną gałąź `feature/demo-generator` z aktualnego `main`. Wcześniejszy błąd 403 dotyczący tej operacji nie wystąpił.
- Przygotowano zapis wszystkich ośmiu plików `demo-generator/` oraz niniejszego audytu przez GitHub API. Kod generatora i jego przykład nie wymagają zmian; wyniki wcześniejszych 13/13 testów pozostają aktualne.

**Stan tego wpisu:** gałąź istnieje, przygotowano commit z plikami; wynik zapisu i porównania zawartości będzie odnotowany w kolejnym wpisie po odczycie danych z GitHub.

**Problemy:** narzędzie odczytu nie przyjęło zakodowanego ukośnika w adresie pojedynczej gałęzi; jej nieistnienie potwierdzono przez listę gałęzi. Nie było to ograniczenie uprawnień zapisu.

**Następne kroki:** opublikować przygotowaną zawartość na nowej gałęzi, porównać wszystkie pliki z wersją lokalną, sprawdzić brak zmian produkcyjnych i niezmieniony SHA `main`, następnie dopisać wynik weryfikacji. Nie tworzyć PR, nie scalać i nie wdrażać na domenę.

### 2026-10-27 — publikacja generatora potwierdzona

**Wynik:** publikacja na GitHub zakończyła się powodzeniem. Gałąź: [feature/demo-generator](https://github.com/Yormiii/Moja-strona/tree/feature/demo-generator).

**Wykonane działania i weryfikacja:**

- Opublikowano komplet generatora oraz audyt w commicie [310e72f](https://github.com/Yormiii/Moja-strona/commit/310e72f8c7afe91effd0d22653587be62ef6410b).
- Ponownie odczytano z GitHub wszystkie 9 zmienionych/dodanych plików: ich pełna treść była identyczna z przygotowaną wersją lokalną.
- Porównanie gałęzi z bazowym `main` wykazało dokładnie osiem nowych plików `demo-generator/` i modyfikację `AUDYT_WEBFORGE.md`; żadnych zmian w plikach produkcyjnych.
- Odczyt listy gałęzi potwierdził, że `feature/demo-generator` wskazuje opublikowany commit, a `main` nadal wskazuje `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`.
- Niniejszy wynik weryfikacji zapisano jako osobną aktualizację dziennika na tej samej gałęzi.
- Nie zmieniano kodu po wcześniejszym pomyślnym przebiegu 13/13 testów; nie powtarzano testów bez zmiany implementacji.
- Nie tworzono Pull Requesta, nie scalano gałęzi i nie publikowano generatora na domenie. Nie konfigurowano płatnych usług.

**Problemy:** wcześniejsza blokada 403 zapisu została rozwiązana przez aktualizację uprawnień. Ograniczenie podglądu wizualnego z poprzedniego zadania pozostaje otwarte.

**Następne kroki:** użytkownik może przeglądać i pobrać kod z gałęzi; następnie sprawdzić lokalnie wygląd demonstracji w przeglądarce i zlecić kolejny etap. PR, scalanie, wdrożenie i zmiany produkcyjne wymagają osobnego polecenia.

### 2026-10-27 — Zadanie 2: wiele firm, automatyczne warianty i katalog demonstracji

**Zakres i ważna informacja właściciela:** pracować wyłącznie na `feature/demo-generator`, bez zmian głównej witryny i gałęzi `main`, bez płatnych usług. Właściciel poinformował, że Cloudflare Pages automatycznie publikuje tę gałąź. Zapis zmian jest zatem publikacją; wszystkie nowe dane i wyniki muszą być fikcyjne i pozbawione poufnych informacji. Jest to nowsza informacja niż historyczne wpisy o braku wdrożenia w poprzednich zadaniach.

**Odczyt i stan początkowy:**

- Przeczytano aktualny audyt z GitHub, kod, dane branżowe i szablon generatora oraz drzewo gałęzi `feature/demo-generator`, commit bazowy `712760ecebd76befe90ed35daf79df19aad60926`.
- Sprawdzono zgodność lokalnych plików z blobami GitHub. `main` przed publikacją nadal wskazywał `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`.

**Wykonane działania:**

- Generator v0.2 przyjmuje JSON pojedynczej firmy (zgodność wsteczna) albo tablicę 1–1000 firm. Dla każdej tworzy osobny `generated/<slug>/index.html`.
- Dodano automatyczny wybór jednego z czterech wariantów na podstawie ośmiu branż. Mechanik, elektryk i hydraulik używają układu usługowego; barber i beauty — salonowego; restauracja — gastronomicznego; kancelaria i trener — eksperckiego. Warianty różnią się panelem branżowym i układem/typografią; wspólna baza nadal pochodzi z istniejących demonstracji.
- Kolory, etykiety i CTA są wybierane z konfiguracji branży. Pole `kolory` pozostaje opcjonalnym nadpisaniem. Wybór wariantu nie przyjmuje ścieżki od użytkownika.
- Dodano `templates/catalog.html` i katalog `generated/index.html`, z bezpiecznymi względnymi linkami do wszystkich istniejących demonstracji. Tytuły są kodowane jako tekst.
- Katalog jest odbudowywany na podstawie istniejących podkatalogów i plików `index.html`; rozpoznaje także wcześniejsze demo v0.1 bez manifestu. Nie gromadzi dodatkowych danych kontaktowych.
- Dodawanie nowych firm nie usuwa poprzednich wyników. Pominięte firmy zachowują pliki i linki w katalogu. Identyczne wyniki są pomijane, a odświeżenie zmienionej strony wymaga `--force`. Flaga obejmuje tylko firmy z bieżącego wejścia.
- Cała paczka, unikalność slugów, kolizje, stare wyniki i docelowy katalog są sprawdzane przed zapisem stron. Błędna firma albo późniejsza kolizja nie powoduje częściowego zapisania wcześniejszych firm. Blokada `.generator.lock` chroni przed równoległymi procesami; katalog jest zapisywany przez plik tymczasowy i atomową zmianę nazwy.
- Zachowano walidację danych, zabezpieczenia przed XSS, niebezpiecznymi URL, ścieżkami i symlinkami. Katalog oraz nowe strony mają oznaczenia demonstracyjne i `noindex, nofollow`.
- Dodano `examples/lista-firm.json` z czterema wyłącznie fikcyjnymi firmami. Zachowano przykład Serwis Orbita TEST oraz dodano Salon Próbka TEST, Bistro Piksel TEST i Kancelaria Model TEST. Kontakty to domeny `.invalid`, a numer poprzedniego przykładu jest zerowy. Nie dodano prawdziwych danych potencjalnych klientów ani poufnych informacji.
- Wygenerowano cztery demonstracje i katalog. Poprzednie demo zachowano pod tym samym adresem, odświeżając je do nowego wariantu w kontrolowanym przebiegu z `--force`.
- Zaktualizowano instrukcję i dodano skrypt `npm run generate:batch`. Kolejne firmy dopisuje się do JSON, bez edytowania kodu.
- Dodano testy paczek oraz odizolowano testy CLI, aby ich strony testowe nie zmieniały katalogu przeznaczonego do publikacji.

**Uruchamianie:**

```sh
node demo-generator/generate.mjs demo-generator/examples/lista-firm.json
# Jawne odświeżenie zmienionych stron:
node demo-generator/generate.mjs demo-generator/examples/lista-firm.json --force
npm --prefix demo-generator test
```

Katalog wynikowy: `demo-generator/generated/index.html`. Własna lista może zawierać wyłącznie nowe firmy; poprzednich demonstracji nie trzeba ponownie wpisywać. W CI należy zachować wersjonowane `generated/`, ponieważ pusty katalog roboczy nie zawiera historii poprzedniego wdrożenia. Nie zmieniano konfiguracji budowania w Cloudflare.

**Wyniki testów i kontroli:**

- **26/26 przypadków przeszło, 0 błędów**: 13 dotychczasowych (zaktualizowanych do nowych zasad identycznych wyników) i 13 nowych testów paczek.
- Potwierdzono osiem branż i cztery automatyczne warianty, domyślne kolory, generowanie listy, katalog wszystkich wyników, zachowanie poprzednich stron bajt po bajcie przy dopisywaniu nowych, starsze demo bez manifestu, idempotencję, zmianę tylko wskazanych firm z `--force`, walidację całej paczki i kolizje bez częściowego zapisu.
- Sprawdzono noindex, oznaczenia demonstracji, XSS w danych i starszych tytułach, poprawność linków katalogu, symlinki pliku katalogowego/starszej strony/ścieżki nadrzędnej, blokadę równoległego procesu oraz obsługę listy przez CLI bez edycji kodu.
- `npm --prefix demo-generator test`, osobne przebiegi obu plików testowych i `node --check demo-generator/generate.mjs` zakończyły się powodzeniem. Z powodu sposobu raportowania w tym środowisku tryb `--test` pokazuje 2 zbiorcze pliki; bezpośrednie uruchomienia potwierdziły łącznie 26 przypadków.
- Ponowny przebieg na dołączonej liście zgłosił cztery wyniki „bez zmian”; katalog obejmuje cztery demonstracje.
- Kontrola HTML pięciu plików (cztery strony i katalog) potwierdziła noindex, brak formularzy i skryptów oraz istnienie wszystkich czterech docelowych plików wskazanych w katalogu.
- Sprawdzono SHA wszystkich 16 plików produkcyjnych: identyczne z bazą GitHub. Zmiany ograniczono do `demo-generator/` i audytu.
- Nie deklarowano nowych testów wizualnych w przeglądarce; wcześniejsza blokada środowiska pozostaje opisana w dzienniku.

**Problemy i poprawki w trakcie prac:**

- W pierwszym przebiegu testów dwie asercje CLI odpowiadały starym zasadom kolizji; poprawiono je: identyczna strona jest teraz pomijana, zmieniona nadal wymaga `--force`.
- Nowy test próbował oceniać stdout procesu potomnego, przechwytywany przez środowisko testowe; zastąpiono to sprawdzeniem faktycznej zawartości wygenerowanego katalogu i linków.
- Nieoczekiwany błąd dysku w trakcie zapisu może pozostawić ukończoną część paczki. Po usunięciu przyczyny należy ponowić wejście; identyczne strony są bezpiecznie pomijane. Walidacja i zwykłe kolizje są wykrywane przed zapisem.
- Po awarii procesu blokada może pozostać; usuwać ją ręcznie dopiero po sprawdzeniu, że generator już nie działa.

**Publikacja i następne kroki:**

- Po przejściu testów przygotowano zapis zmian na tej samej gałęzi GitHub. Wynik odczytu po publikacji zostanie odnotowany osobno.
- Nie zmieniano `main`, głównej strony, formularzy, domeny, DNS ani konfiguracji Cloudflare; nie użyto płatnych usług i nie tworzono PR.
- Publikacja gałęzi może uruchomić istniejącą integrację Cloudflare Pages zgodnie z informacją użytkownika. Udostępniane przykłady zawierają wyłącznie dane fikcyjne; rzeczywistego statusu wdrożenia nie należy utożsamiać z samym commitem GitHub.
- Następnie sprawdzić zawartość gałęzi i katalog w istniejącym podglądzie Cloudflare, a w kolejnym zadaniu ewentualnie dodać zdjęcia lub panel. Statusy aktywności i automatyczne usuwanie demonstracji nie są częścią tej wersji.

### 2026-10-27 — potwierdzenie publikacji wersji v0.2

- Opublikowano wersję z listą firm, wariantami i katalogiem w commicie [6f03ebe](https://github.com/Yormiii/Moja-strona/commit/6f03ebe8a22cf53e8337a9d70a040d674837a3cf).
- Gałąź: [feature/demo-generator](https://github.com/Yormiii/Moja-strona/tree/feature/demo-generator).
- Ponownie odczytano z GitHub wszystkie 20 plików objętych przygotowanym zestawem (19 plików generatora i audyt); ich pełna treść była zgodna z wersją lokalną.
- Sprawdzono drzewo GitHub: wszystkie 16 plików produkcyjnych ma niezmienione SHA. Lista gałęzi potwierdziła niezmieniony `main` i nowy commit na `feature/demo-generator`.
- Dołączony katalog: [demo-generator/generated/index.html](https://github.com/Yormiii/Moja-strona/blob/feature/demo-generator/demo-generator/generated/index.html). To link do pliku w repozytorium; adres podglądu Cloudflare zależy od istniejącej konfiguracji.
- Potwierdzono zapis w GitHub. Nie deklarowano osobnego sprawdzenia stanu wdrożenia Cloudflare ani nowych testów wizualnych. Uwzględniono automatyczną publikację tej gałęzi wskazaną przez właściciela: wszystkie nowe firmy i kontakty są fikcyjne.
- Wyniki testów: 26/26 przypadków, kontrola składni i HTML pozytywne. Nie było potrzeby ponawiania testów kodu po tej dokumentacyjnej aktualizacji.
- Nie użyto płatnych usług, nie tworzono PR i nie scalano z `main`.

**Następny krok:** sprawdzić wygląd czterech wariantów i katalogu w istniejącym podglądzie Cloudflare; kolejne fikcyjne firmy można dodawać przez sam JSON i ponowny przebieg generatora.

### 2026-10-27 — WebForge Prospect Finder v0.1

**Zakres:** osobny moduł na `feature/demo-generator`, bez zmian `main` i produkcyjnej strony. Pamiętano o automatycznej publikacji gałęzi przez Cloudflare Pages. Nie uruchamiano wysyłki, publikacji demo rzeczywistych firm ani płatnych API.

**Stan wejściowy i decyzje:**

- Przeczytano audyt i drzewo gałęzi, commit bazowy `59c9b0b1f900dfe3765a8d32ed54711d2c786056`. `main` na początku wskazywał `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`.
- W repozytorium odnaleziono osiem profili generatora, ale nie zatwierdzoną listę 30 branż. Zadano opcjonalne pytanie o tę listę; wobec braku odpowiedzi przygotowano w konfiguracji jawną listę **roboczą do potwierdzenia**, zamiast przypisywać jej status wcześniejszych ustaleń.
- Pierwsza wersja korzysta z danych fikcyjnych i lokalnego importu publicznych danych w JSON. Nie jest to jeszcze automatyczne pobieranie firm z internetu ani automatyczny audyt witryn. Taki zakres jest zgodny z dopuszczeniem danych testowych w zadaniu.

**Wykonane działania:**

- Dodano osobny `prospect-finder/`: Python 3.10+ i SQLite z biblioteki standardowej, bez zależności, API i nowych usług.
- `config/industries.json`: 30 roboczych branż obejmujących usługi lokalne, beauty, motoryzację, budowę i remonty, gospodarstwa, agroturystykę, noclegi, gastronomię i usługi profesjonalne; mapowanie na istniejące profile wizualne generatora.
- `config/locations.json`: 16 województw, Polska, przykładowe zapisane wyszukiwania. Filtry obsługują dowolne miasto, województwo i cały kraj, również w połączeniu. Modernizacja istniejących stron jest osobną kategorią niezależną od branży.
- `SourceAdapter` i `JsonFileSource`: kontrakt do dalszych źródeł oraz działające adaptery `test-json` i `public-json`. Brak wywołań HTTP. Publiczny import wymaga pliku poza repozytorium i udokumentowanego pochodzenia.
- Dla firm przechowywane są nazwa, branża, kraj/miasto/województwo/adres, opcjonalna strona, kontakty z osobnymi źródłami i datami, identyfikatory i linki źródeł, data ostatniej weryfikacji, oznaki aktywności oraz potwierdzone fakty. Import nie przyjmuje statusów, zgód ani sekretów jako dodatkowych pól.
- Punktacja 0–100 z rozłącznymi ścieżkami: brak strony do 50 punktów albo przestarzałość/mobile/oferta/technika 15+15+10+10. Aktywność do 20 i udokumentowany potencjał do 30. Każdy składnik ma uzasadnienie, dowody i datę.
- Fakty starsze niż 180 dni nie dają punktów. Puste WWW nie oznacza braku strony; brak oznak działalności pozostaje stanem nieustalonym. Osobne pokrycie danych nie jest pewnością statystyczną ani prawdopodobieństwem zakupu.
- Lokalna SQLite przechowuje rekordy, tożsamości źródeł, historię statusów i zablokowane zdarzenia automatyzacji. Deduplikacja używa ID w źródle albo normalizowanej nazwy i pełnej lokalizacji/adresu. Nie scala samych wspólnych domen/telefonów ani oddziałów o innych adresach. Import jest transakcyjny i nie resetuje statusów; starsze informacje nie nadpisują nowszych pól.
- Dodano dziewięć statusów wymaganych w zadaniu i kontrolowane przejścia. Publiczny kontakt lub wysoka ocena nie nadają automatycznie statusu „kontakt dozwolony”. Ten status wymaga jawnego potwierdzenia z datą i źródłem; zmiana kanałów lub przeterminowanie blokują dalsze oznaczenie kontaktu.
- Akceptacja wymaga kompletności danych do szkicu demo. Adapter `demo-input` tworzy wyłącznie JSON poza repozytorium, bez HTML, publikacji czy wysyłki. Nie wymyśla brakujących usług, opisu ani kontaktów.
- Dodano eksport CSV i JSON z oceną i źródłami; CSV jest zabezpieczony przed interpretacją formuł. Eksport nie nadpisuje istniejących plików.
- Baza domyślnie powstaje w `~/.local/share/webforge-prospects/`. Program odmawia zapisu baz, eksportów i szkiców w repozytorium. Nie dodano żadnej bazy ani prywatnego eksportu do Git.
- Dodano responsywny panel `panel.html` / `panel.css` / `panel.mjs` do Safari/iPada. Otwiera eksport z Plików, filtruje i pokazuje dowody, przygotowuje plik decyzji. Nie przesyła danych, nie używa fetch, cookies ani localStorage; CSP blokuje połączenia sieciowe. Zmiany bazy wymagają lokalnego `apply-decisions`, transakcji i zgodnego `expected_status`.
- To panel offline-first, nie publiczny serwer SQLite. Import/eksport i zastosowanie decyzji wymagają środowiska Python na komputerze lub prywatnym serwerze; nie zadeklarowano pełnej pracy backendu wyłącznie na iPadzie. Udostępnienie panelu w istniejącym podglądzie zależy od katalogu publikacji Cloudflare; konfiguracji hostingu nie zmieniano.
- `config/automation.json` i tabela `automation_events` przygotowują kontrakt pod szkice/publikację demo, personalizację wiadomości, odpowiedzi, Telegram, wyceny i strony finalne po akceptacji. Wszystkie akcje są wyłączone, zdarzenia mają `state: blocked`; nie ma workerów ani kodu wysyłki.
- `fixtures/companies.json`: cztery wyraźnie fikcyjne firmy i jeden duplikat; wszystkie kontakty/źródła to domeny `.invalid`. `fixtures/panel-demo.json` to również wyłącznie fikcyjny eksport do demonstracji panelu. Jego tymczasową bazę usunięto po utworzeniu.
- Jedyna zmiana funkcjonalna istniejącego generatora: dwa opcjonalne, walidowane i kodowane pola `etykieta_branzy` i `cta`. Dzięki nim profil wizualny z ośmiu branż można wykorzystać dla pozostałych branż bez błędnej etykiety i bez przebudowy układu. Zaktualizowano instrukcję tych pól. Dotychczasowe dane i wszystkie wygenerowane demonstracje pozostały bajtowo zgodne z bazą.
- Dodano obszerną instrukcję modułu i testy.

**Weryfikacja:**

- **58/58 przypadków przeszło, 0 błędów:** 27 testów Python/SQLite/CLI, 5 testów panelu i mostu, 26 dotychczasowych testów generatora.
- Testy objęły lokalizacje, modernizację niezależną od branży, źródła/daty, nieustalone i stare dane, oba warianty punktacji do 100, deduplikację i oddziały, zachowanie nowszych informacji/statusów, transakcyjność, dziewięć statusów, potwierdzenia kontaktu i ich świeżość, decyzje z optymistyczną kontrolą wersji, CSV/JSON, ochronę ścieżek, trwałość bazy oraz cały przebieg CLI.
- Test integracyjny potwierdził poprawne wejście istniejącego generatora dla wszystkich 30 branż. Akceptacja niekompletnych rekordów jest blokowana. Nie utworzono żadnego HTML rzeczywistej firmy.
- Testy panelu sprawdzają walidację eksportu, niebezpieczne linki, wymaganie podstawy kontaktu i brak kodu wysyłki/HTML z danych. Nie przeprowadzono nowej wizualnej weryfikacji Safari/iPada; wcześniejsze ograniczenie przeglądarki w środowisku pozostaje aktualne.
- Ponownie sprawdzono wyłącznie fikcyjny charakter obu publikowanych zbiorów. Bazy testowe i robocze eksporty były w usuwanych katalogach tymczasowych poza repozytorium.
- Wersja testowa środowiska: Python 3.12.14 i Node.js 24.19.0. Brak opłat za biblioteki/API.

**Ograniczenia i następne kroki:**

1. Potwierdzić lub podmienić roboczą listę 30 branż w JSON.
2. Sprawdzić panel w Safari i możliwość udostępnienia jego statycznego katalogu przez istniejący podgląd; nie wystawiać SQLite ani eksportów publicznie.
3. W osobnym zadaniu podłączyć wybrane publiczne źródło po weryfikacji jego dostępu, warunków i schematu; obecne „find” przeszukuje importowany plik, nie internet.
4. Deduplikacja jest konserwatywna — warianty nazw i niejednoznaczne tożsamości mogą wymagać ręcznej weryfikacji. Ocena sprzedażowa jest jawną oceną źródła/reviewera, nie pomiarem rynku ani domysłem AI.
5. Nie uruchamiać automatycznej komunikacji, Telegrama, publikacji rzeczywistych firm ani stron finalnych bez osobnych zadań i akceptacji. JSON szkicu nie może trafić przypadkiem do publicznego katalogu generatora.
6. Po testach opublikować wyłącznie kod, fikcyjne przykłady i audyt na właściwej gałęzi oraz potwierdzić zawartość GitHub i niezmieniony `main`. Nie tworzyć PR i nie scalać.

### 2026-10-27 — publikacja Prospect Finder v0.1 potwierdzona

- Opublikowano moduł w commicie [d829cda](https://github.com/Yormiii/Moja-strona/commit/d829cdac9b9bd055fdb6ea4165ac06710ecb1e7f) na [feature/demo-generator](https://github.com/Yormiii/Moja-strona/tree/feature/demo-generator).
- Ponownie odczytano wszystkie 18 publikowanych plików; ich pełna zawartość była identyczna z przygotowaną wersją lokalną.
- Zweryfikowano drzewo GitHub: 33 istniejące pliki poza trzema świadomie modyfikowanymi (audyt, kod i instrukcja generatora) zachowały SHA. Dotyczy to wszystkich 16 plików produkcyjnych i wszystkich istniejących demonstracji.
- W opublikowanym drzewie nie ma SQLite, plików bazy ani cache Pythona. Wszystkie dane przykładów są jawnie fikcyjne.
- Lista gałęzi potwierdziła nowy commit na właściwej gałęzi i niezmieniony `main` (`8f07e41bdfad0d491b4d617c8a23a25a9465bb72`).
- Wyniki testów: 58/58. Nie wysłano wiadomości, nie opublikowano demo rzeczywistej firmy, nie skonfigurowano płatnego API, nie tworzono PR i nie scalano z `main`.
- Potwierdzono zapis w GitHub; nie deklarowano osobnej weryfikacji wdrożenia Cloudflare ani wizualnego testu Safari. Backend pozostaje lokalny, a panel służy do plików eksportu i decyzji.
- Lista 30 branż pozostaje oznaczona jako robocza; live discovery i podłączenie konkretnego publicznego źródła wymagają następnego zadania.

**Następne kroki:** potwierdzić listę branż, sprawdzić fikcyjny eksport w panelu na iPadzie i wybrać pierwsze rzeczywiste źródło do osobnego podłączenia. Zachować prywatne bazy i eksporty poza publicznie wdrażanym repozytorium.

### 2026-10-27 — Prospect Finder v0.2: OpenStreetMap i kontrola stron WWW

**Kontynuacja po przerwaniu:** przed przerwaniem odczytano istniejący kod, audyt i zasady źródła oraz sprawdzono sieć; nie było jeszcze zapisanej implementacji v0.2. Po wznowieniu zachowano bazę projektu i dokończono moduł na tej samej gałęzi. Bazowy commit GitHub: `b8c08b3118d1e06772f5ec2ebad6f84e337a18ac`.

**Wykonane działania:**

- Dodano adapter `OverpassSource` w `prospect-finder/live.py` i polecenie `discover`. Istniejące importy JSON, SQLite, deduplikacja, statusy, punktacja i most do generatora pozostają dostępne.
- `config/osm.json` zawiera mapowanie tagów dla wszystkich 30 aktualnie skonfigurowanych branż i region Poznań: centrum 52.4064/16.9252, promień 30 km, województwo wielkopolskie. Lista branż zachowuje roboczy status ustalony w poprzednim zadaniu.
- Powstaje jedno zbiorcze zapytanie Overpass, z czasem 25 s, deklaracją pamięci 64 MiB i maks. 1500 obiektami. Nie używa się geokodera, map kafelkowych ani ręcznie wpisanych firm. Próba wybiera maks. 25 (konfigurowalnie 1–30) rekordów, naprzemiennie według znalezionych branż, w kolejności od najbliższych punktów.
- Nazwy, adresy, publiczne kontakty i WWW pochodzą wyłącznie z tagów OSM; każdy rekord ma link do obiektu OSM, datę odczytu, współrzędne i atrybucję. Brak miasta zapisuje się jako nieustalony, zamiast przypisywać wszystkim firmom Poznań. Zamknięte/porzucone obiekty i obiekty z access=private są pomijane.
- Niepełny, błędny lub oznaczony remarkiem wynik Overpass nie jest importowany jako kompletne wyszukiwanie. Mapowanie jest heurystyczne i wymaga sprawdzenia: np. myjnia nie potwierdza detailingu, a centrum fitness osobistego trenera.
- `network.py` zapewnia standardowy klient HTTP z domyślną weryfikacją TLS, odziedziczonym proxy, wyłączonymi automatycznymi przekierowaniami i kontrolą adresów przed żądaniem. Odrzuca lokalne/prywatne adresy, nieobsługiwane porty i dane logowania. To narzędzie lokalne, nie publiczny proxy; ochrona URL/DNS nie zastępuje polityki egress ani nie gwarantuje pełnej ochrony przed DNS rebinding.
- `config/network.json`: maks. 100 żądań w przebiegu, 200 na dzień, 10 Overpass na dzień; przerwy na host 2 s, Overpass 10 s; maks. 3 próby, narastające opóźnienie i jitter, respektowanie Retry-After także dla innych ścieżek hosta. Zbyt długie odroczenie wstrzymuje zapytania zamiast ponawiać je za wcześnie.
- Limity odpowiedzi 1 MiB dla strony i 8 MiB dla Overpass, 50 MiB na dzień, maks. 3 przekierowania; błędne próby rezerwują pełny limit pobierania. Limity i cache są trwałe w prywatnym SQLite, nie zerują się po ponownym uruchomieniu.
- Cache: WWW 6 godzin, Overpass 24 godziny, odpowiedzi błędne 5 minut lub dłuższy Retry-After. Ciepły cache działa bez DNS i zachowuje datę pierwotnego pobrania.
- `SiteAuditor` sprawdza robots.txt i tylko stronę główną. Respektuje odmowę i Crawl-delay; błędy lub nieobsługiwane przekierowania robots powodują pominięcie, a 404 robots dopuszcza odczyt. Przy przekierowaniu na inny host ponownie sprawdzana jest polityka robots. Nie pobiera zasobów ani formularzy, nie wykonuje JS i nie wysyła wiadomości.
- Dostępność jest zapisywana osobno w `site_check`: reachable, http_error, access_limited, robots_disallowed, network_error, budget_exceeded lub no_url. HTTP 404/410 i 5xx są udokumentowanymi technicznymi sygnałami pojedynczego pomiaru; nie oznaczają braku strony ani nieaktywności.
- Brak tagu WWW lub website=no w OSM pozostaje unknown. Brak strony może nadal być potwierdzony ręcznym, udokumentowanym faktem z dotychczasowego modułu, ale nie jest zgadywany z niepełnej mapy, timeoutu lub 404.
- Flash/frameset jest punktowaną oznaką starej technologii. Brak meta viewport i zasoby HTTP przy HTTPS pozostają jedynie wskazówkami do kontroli, bez automatycznych punktów za mobile/awarię. Nie sprawdza się wieku domeny ani nie ocenia wyglądu na jego podstawie.
- Data edycji OSM i działające WWW nie dają automatycznych punktów aktywności firmy ani potencjału sprzedażowego. Kategorie i ocena 0–100 nadal wykorzystują dowody; modernizacja pozostaje niezależna od branży.
- JSON/CSV zachowują współrzędne, metadane licencji i wynik audytu. Panel nadal działa na prywatnym eksporcie; dodano wyświetlanie atrybucji, współrzędnych i diagnostyki WWW.
- Kod adapterów jest oddzielony od transportu i magazynu, co umożliwia dodawanie kolejnych źródeł. Nie dodano płatnych API, publikacji demo rzeczywistych firm ani workerów komunikacji.

**Zasady źródła:** sprawdzono [Overpass — Commons](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) i [OpenStreetMap — licencja](https://www.openstreetmap.org/copyright). To współdzielony serwer; prototyp stosuje małe zapytania i limity, bez przełączania serwerów w celu obchodzenia ograniczeń. Atrybucja „© OpenStreetMap contributors”, ODbL i link licencji są zachowane przy danych. Nie uruchomiono masowej ani wieloużytkownikowej usługi na publicznym Overpass.

**Próba rzeczywista i ograniczenie środowiska:**

- Uruchomiono gotowe polecenie z limitem 25 rzeczywistych firm dla regionu poznan.
- **Rzeczywiście znalezione firmy: 0. Zapisane unikalne rekordy: 0. Wyeksportowane rekordy: 0.** Nie zastąpiono ich danymi fikcyjnymi i nie osiągnięto celu 20–30 firm z powodu środowiska sieciowego.
- Pierwszy test urllib zwrócił `Operation not permitted`. Próba z dodatkowym uprawnieniem sieciowym została przerwana przy przerwaniu zadania. Gotowy moduł po wznowieniu zwrócił `blocked_or_failed`, kod 2 i informację o braku bezpiecznego rozpoznania DNS. Do wykonania żądania HTTP Overpass nie doszło.
- Raport: `/workspace/webforge-private/prospect-finder-v02/live/20261027T224108Z-9167ec32-report.json`. Baza i cache próby znajdują się w tym samym prywatnym drzewie, poza `/workspace/WebForge` i katalogiem Cloudflare. SQL potwierdził pustą bazę wyników.
- Nie obchodzono proxy, blokad sieci ani weryfikacji TLS. Nie stwierdzono awarii samego Overpass na podstawie ograniczenia wykonawcy.

**Testy i dokumentacja:**

- **81/81 przypadków przeszło, 0 błędów:** 50 testów Python (27 wcześniejszych i 23 sieciowe z symulowanymi odpowiedziami), 5 panelu/mostu oraz 26 regresyjnych generatora.
- Sprawdzono pokrycie 30 branż w zapytaniu, klasyfikację, zakres geograficzny, kontakty i atrybucję, unknown bez WWW, pomijanie zamkniętych obiektów, cache/wygaśnięcie i pracę bez DNS, limity per host/przebieg/dzień, opóźnienia, Retry-After, błędy sieci, wielkość odpowiedzi i budżet pobierania.
- Sprawdzono robots i Crawl-delay także dla kolejnego rekordu hosta, blokowanie prywatnych przekierowań i produkcyjnego hosta, brak fałszywych punktów po błędzie sieci, potwierdzone legacy markup, wskazówki mobile oraz pełny syntetyczny przebieg discovery → SQLite → prywatne eksporty i deduplikację przy ponownym odczycie.
- W testach są wyłącznie syntetyczne firmy i odpowiedzi; nie są one liczone jako rzeczywiste wyniki. Nie dodano żadnych prawdziwych rekordów, stron, cache, baz ani eksportów do repozytorium.
- Zaktualizowano README: polecenia uruchamiania, limity, licencja, charakter ocen, kody wyjścia, wynik próby 0 i miejsce danych. Składnia wszystkich trzech modułów Python została sprawdzona.
- Przy przeglądzie poprawiono zachowanie długiego Retry-After dla całego hosta i Crawl-delay przy kolejnych rekordach; ponowne testy przeszły. Cache nie wykonuje zbędnego DNS, gdy ma aktualną odpowiedź.
- Testy wizualne i produkcyjne połączenia HTTP do stron firm nie były możliwe; odpowiedzi sieciowe w testach są symulowane.

**Następne kroki:**

1. Uruchomić podane w README `discover --region poznan --limit 25` w prywatnym środowisku z działającym DNS/HTTPS. Zachować bazę/cache/eksporty poza repozytorium; uzyskanie 20–30 rzeczywistych rekordów nadal wymaga tego przebiegu.
2. Ręcznie zweryfikować klasyfikację, źródła, aktualność kontaktów i ewentualne oznaki braku strony lub przestarzałości. Nie traktować próbki OSM jako potwierdzonej listy klientów do kontaktu.
3. Potwierdzić listę 30 branż i rozważyć osobne źródło dla słabo reprezentowanych rzemieślników i gospodarstw. Nie zwiększać agresywnie zapytań publicznego Overpass.
4. Po testach zapisać wyłącznie kod/dokumentację i audyt na `feature/demo-generator`, potwierdzić brak zmian `main` i produkcyjnych plików. Nie tworzyć PR, nie publikować demo rzeczywistych firm i nie wysyłać wiadomości.
