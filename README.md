![Logo Proiect](images/logo.png)
# 🔥 **CMTEB Termoficare - 🏠 Integrare pentru Home Assistant**

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-23.11.2025.a-blue.svg)](https://github.com/your-username/cmteb_termoficare)
[![Home Assistant](https://img.shields.io/badge/Home_Assistant-2023.1%2B-green.svg)](https://www.home-assistant.io/)

Integrare pentru monitorizarea în timp real a întreruperilor in furnizarea agentului termic a Companiei Municipale TERMOENERGETICA București.


---

## 🚀 Caracteristici

### ✨ Funcționalități Principale
- ✅ **Monitorizare în timp real** a întreruperilor la termoficare
- ✅ **Sistem inteligent de căutare** cu recunoaștere prescurtări
- ✅ **Configurare grafică** - fără editare manuală YAML
- ✅ **Senzori cu nume semnificative** bazate pe adresă
- ✅ **Actualizare automată** la fiecare 30 de minute
- ✅ **Support pentru multiple adrese** simultan
- ✅ **Carduri Lovelace personalizate** incluse

### 🔍 Sistem Inteligent de Căutare
Integrarea recunoaște automat toate variantele de scriere pentru străzi:

| Tu introduci: | Site-ul CMTEB afișează: | Rezultat: |
|---------------|-------------------------|-----------|
| `str Moisil` | `Strada Grigore C. Moisil` | ✅ **Potrivire** |
| `bd. Unirii` | `Bulevardul Unirii` | ✅ **Potrivire** |
| `Sos Pantelimon` | `Şoseaua Pantelimon` | ✅ **Potrivire** |
| `drm Taberei` | `Drumul Taberei` | ✅ **Potrivire** |
| `p-ta Romană` | `Piața Romană` | ✅ **Potrivire** |

---

## 📦 Instalare

### Metoda 1: Prin HACS (Recomandat)
1. Deschide **HACS** în Home Assistant
2. Click pe **Integrations**
3. Click pe butonul cu 3 puncte (⋮) din colțul dreapta sus
4. Selectează **Custom repositories**
5. Adaugă URL-ul: `https://github.com/GeorgeRPI/cmteb_termoficare`
6. Selectează categoria **Integration**
7. Click **Add**
8. Caută **"CMTEB Termoficare"** în lista de integrări noi
9. Click **Download**
10. **Repornește Home Assistant**

### Metoda 2: Instalare Manuală
1. Descarcă ultima versiune de pe [GitHub Releases](https://github.com/GeorgeRPI/cmteb_termoficare/releases)
2. Copiază directorul `cmteb_termoficare` în `config/custom_components/`
3. Repornește Home Assistant
4. Adaugă integrarea din **Settings → Devices & Services → Add Integration**

---

## ⚙️ Configurare

### Pasul 1: Adaugă Integrarea
1. Mergi la **Settings** → **Devices & Services** → **Integrations**
2. Click pe **Add Integration**
3. Caută **"CMTEB Termoficare"**
4. Click pe integrare pentru a o configura

### Pasul 2: Completează Datele
- **📝 Adresa:** Introdu adresa în orice variantă
- **🏭 Punct Termic (opțional):** Numele punctului termic specific

### 📋 Exemple Adrese Valide
- `"str Grigore C. Moisil"`
- `"bd. Unirii 15"`
- `"Sos Pantelimon"`
- `"drm Taberei"`
- `"p-ta Romană"`
- `"se poate introduce si doar numele strazi"`

---

## 🔧 Senzori Generați

### Structura Senzori
Fiecare adresă adăugată creează 3 senzori unici:

| Senzor | Descriere | Exemplu Valori |
|--------|-----------|----------------|
| `sensor.cmteb_agent_afectat_[nume_adresa_punct_termic]` | Agentul termic afectat | `"ÎNCĂLZIRE"`, `"APĂ CALDĂ"` |
| `sensor.cmteb_cauza_interventie_[nume_adresa_punct_termic]` | Motivul intervenției | `"Defecțiune rețea"` |
| `sensor.cmteb_data_estimata_reparatie_[nume_adresa_punct_termic]` | Data estimată reparare | `"25.11.2025 18:00"` |

### 🏷️ Exemple Nume Senzori
| Adresa Introdusă | Punct termic |Entity ID Generat |
|------------------|-------------------|-------------------|
| `Str Grigore C. Moisil` | `Moisil 1` | `sensor.cmteb_agent_afectat_str_grigore_c_moisil_moisil_1` |
| `Bd. Unirii 15` | `Unirii tronson 2` | `sensor.cmteb_agent_afectat_bd_unirii_15_unirii_tronson_2` |


---

## 🎨 Carduri Lovelace

### 📱 Card 1: Stare Detaliată v.3

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: >
      # 🛣️ {{ state_attr('sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC',
      'Adresa') }}


      ## **🔥 Punct Termic:** {{
      state_attr('sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC', 'Punct_Termic')
      | default('General') }}
    card_mod:
      style: |
        ha-card {
          background: var(--primary-color);
          color: white;
          text-align: center;
          font-weight: bold;
          padding: 15px;
          border-radius: 10px 10px 0 0;
          box-shadow: var(--box-shadow);

        }
        h2 {
          font-size: 1.5em;
          margin-bottom: 10px;
        }
  - type: custom:button-card
    entity: sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC
    name: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE' || entity.state === 'Oprire INC') return '🔥 ÎNCĂLZIRE (INC)';
        if (entity.state === 'APĂ CALDĂ' || entity.state === 'Oprire ACC') return '🚿 APĂ CALDĂ (ACC)';
        if (entity.state === 'Oprire ACC/INC') return 'OPRITĂ<br> 🚿 APA CALDĂ si 🔥 ÎNCĂLZIREA'; 
        if (entity.state === 'Deficienta INC') return '⚠️ DEFICIENTĂ 🔥 INCALZIRE';
        if (entity.state === 'Deficienta ACC') return '⚠️ DEFICIENTĂ 🚿 APA CALDA';
        if (entity.state === 'Deficienta ACC/INC') return '⚠️ DEFICIENTĂ<br> 🚿 APA CALDĂ si 🔥 ÎNCĂLZIRE';
        return '✅ SISTEM FUNCȚIONAL';
      ]]]
    icon: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE' || entity.state === 'APĂ CALDĂ' || entity.state.includes('Deficienta') || entity.state.includes('Oprire')) return 'mdi:alert-circle-outline';
        return 'mdi:check-circle-outline';
      ]]]
    state_display: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE' || entity.state === 'Oprire INC') return '🚨 OPRITĂ';
        if (entity.state === 'APĂ CALDĂ' || entity.state === 'Oprire ACC') return '🚨 OPRITĂ';
        if (entity.state === 'Oprire ACC/INC') return '🚨 OPRITĂ';
        if (entity.state === 'Deficienta INC') return '🚫 DEFICIENTĂ';
        if (entity.state === 'Deficienta ACC') return '🚫 DEFICIENTĂ';
        if (entity.state === 'Deficienta ACC/INC') return '🚫 DEFICIENTĂ';
        return '🟢 ACTIV';
      ]]]
    styles:
      card:
        - background-color: |
            [[[
              if (entity.state === 'ÎNCĂLZIRE' || entity.state === 'APĂ CALDĂ' || 
                  entity.state.includes('Deficienta') || entity.state.includes('Oprire')) return '#ff4444';
              return '#4CAF50';
            ]]]
        - color: white
        - font-weight: bold
        - border-radius: 10px
        - padding: 15px
        - text-align: center
        - box-shadow: var(--box-shadow)
        - border: 2px solid white
      icon:
        - color: white
        - width: 40px
        - height: 40px
      name:
        - font-size: 20px
        - margin-bottom: 8px
        - line-height: 1.2
      state:
        - font-size: 15px
        - font-weight: normal
  - square: false
    type: grid
    columns: 2
    cards:
      - type: custom:button-card
        entity: sensor.cmteb_cauza_interventie_STRADA_PUNCT_TERMIC
        name: 🛠️ Motiv Intervenție
        icon: mdi:hammer-wrench
        show_state: true
        styles:
          card:
            - background-color: var(--card-background-color)
            - border-radius: 8px
            - padding: 12px
            - border-left: 2px solid
            - box-shadow: var(--box-shadow)
          name:
            - font-size: 12px
            - font-weight: bold
            - color: var(--primary-text-color)
          state:
            - font-size: 13px
            - font-weight: normal
            - color: var(--secondary-text-color)
      - type: custom:button-card
        entity: sensor.cmteb_data_estimata_reparatie_STRADA_PUNCT_TERMIC
        name: 📅 Data Reparare
        icon: mdi:calendar-clock
        show_state: true
        styles:
          card:
            - background-color: var(--card-background-color)
            - border-radius: 8px
            - padding: 12px
            - border-left: 2px solid
            - box-shadow: var(--box-shadow)
          name:
            - font-size: 12px
            - font-weight: bold
            - color: var(--primary-text-color)
          state:
            - font-size: 13px
            - font-weight: normal
            - color: var(--secondary-text-color)

```
### 📱 Card 2: Stare Detaliată v.2

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: >
      # 🏘️ {{ state_attr('sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC',
      'Adresa') | default('Locație') }}
    card_mod:
      style: |
        ha-card {
          background: var(--primary-color);
          color: white;
          text-align: center;
          font-weight: bold;
          padding: 15px;
          border-radius: 10px 10px 0 0;
          box-shadow: var(--box-shadow);
        }
  - type: markdown
    content: >
      ## 🛣️ Stradă: {{
      state_attr('sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC', 'Adresa') }}

      ## 🔥 Punct Termic: {{
      state_attr('sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC',
      'Punct_Termic') | default('General') }}
    card_mod:
      style: |
        ha-card {
          background: var(--card-background-color);
          padding: 15px;
          border-left: 4px solid var(--primary-color);
        }
  - type: custom:button-card
    entity: sensor.cmteb_agent_afectat_STRADA_PUNCT_TERMIC
    name: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE') return '🔥 ÎNCĂLZIRE (INC)';
        if (entity.state === 'APĂ CALDĂ') return '🚿 APĂ CALDĂ (ACC)';
        if (entity.state.includes('Deficienta')) return '⚠️ ' + entity.state;
        return '✅ FUNCȚIONAL';
      ]]]
    icon: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE') return 'mdi:radiator-disabled';
        if (entity.state === 'APĂ CALDĂ') return 'mdi:water-off';
        if (entity.state.includes('Deficienta')) return 'mdi:alert-circle-outline';
        return 'mdi:check-circle-outline';
      ]]]
    state_display: |
      [[[
        if (entity.state === 'ÎNCĂLZIRE') return '🔴 OPRIȚĂ';
        if (entity.state === 'APĂ CALDĂ') return '🔴 OPRIȚĂ';
        if (entity.state.includes('Deficienta')) return '🔵 DEFICIENT';
        return '🟢 ACTIV';
      ]]]
    styles:
      card:
        - background-color: |
            [[[
              if (entity.state === 'ÎNCĂLZIRE' || entity.state === 'APĂ CALDĂ') return '#ff4444';
              if (entity.state.includes('Deficienta')) return '#2196F3';
              return '#4CAF50';
            ]]]
        - color: white
        - font-weight: bold
        - border-radius: 10px
        - padding: 20px
        - text-align: center
        - box-shadow: var(--box-shadow)
        - border: 2px solid white
      icon:
        - color: white
        - width: 35px
        - height: 35px
      name:
        - font-size: 23px
        - margin-bottom: 8px
      state:
        - font-size: 14px
        - font-weight: normal
  - type: grid
    columns: 2
    square: false
    cards:
      - type: custom:button-card
        entity: sensor.cmteb_cauza_interventie_STRADA_PUNCT_TERMIC
        name: 🛠️ Cauza
        icon: mdi:hammer-wrench
        show_state: true
        styles:
          card:
            - background-color: var(--card-background-color)
            - border-radius: 8px
            - padding: 12px
            - border-left: 4px solid
            - box-shadow: var(--box-shadow)
          name:
            - font-size: 12px
            - font-weight: bold
            - color: var(--primary-text-color)
          state:
            - font-size: 13px
            - font-weight: normal
            - color: var(--secondary-text-color)
      - type: custom:button-card
        entity: sensor.cmteb_data_estimata_reparatie_STRADA_PUNCT_TERMIC
        name: 📅 Data Reparare
        icon: mdi:calendar-clock
        show_state: true
        styles:
          card:
            - background-color: var(--card-background-color)
            - border-radius: 8px
            - padding: 12px
            - border-left: 4px solid
            - box-shadow: var(--box-shadow)
          name:
            - font-size: 12px
            - font-weight: bold
            - color: var(--primary-text-color)
          state:
            - font-size: 13px
            - font-weight: normal
            - color: var(--secondary-text-color)

```

### 📱 Card 3: Stare Detaliată v.1

```yaml
type: custom:vertical-stack-in-card
title: 🔥 Status Termoficare CMTEB
cards:
  - type: conditional
    conditions:
      - entity: sensor.cmteb_agent_afectat_STRADA
        state_not: "Fără întreruperi"
    card:
      type: markdown
      content: |
        ### ⚠️ ÎNTRERUPERE ACTIVĂ
        **Locație:** {{ states.sensor.cmteb_agent_afectat_STRADA.attributes.Adresa }}
        **Agent afectat:** {{ states.sensor.cmteb_agent_afectat_STRADA.state }}
        **Cauză:** {{ states.sensor.cmteb_cauza_interventie_STRADA.state }}
        **Data estimată reparare:** {{ states.sensor.cmteb_data_estimata_reparatie_STRADA.state }}
      card_mod:
        style: |
          ha-card {
            background: var(--warning-color);
            color: var(--primary-text-color);
            border-left: 4px solid var(--error-color);
            padding: 15px;
          }
  - type: conditional
    conditions:
      - entity: sensor.cmteb_agent_afectat_STRADA
        state: "Fără întreruperi"
    card:
      type: markdown
      content: |
        ### ✅ NICI O ÎNTRERUPERE
        **Locație:** {{ states.sensor.cmteb_agent_afectat_STRADA.attributes.Adresa }}
        **Status:** Toate serviciile funcționează normal 🎉
      card_mod:
        style: |
          ha-card {
            background: var(--success-color);
            color: white;
            padding: 15px;
          }
  - type: entities
    entities:
      - entity: sensor.cmteb_agent_afectat_STRADA
        name: Agent Termic Afectat
        icon: mdi:fire-circle
      - entity: sensor.cmteb_cauza_interventie_STRADA
        name: Motivul Intervenției
        icon: mdi:tooltip-text
      - entity: sensor.cmteb_data_estimata_reparatie_STRADA
        name: Data Estimată Reparare
        icon: mdi:calendar-check
    title: Detalii Tehnice

````
---
## 🔔 Automatizări

### 📢 Alertă Notificare Întrerupere

```yaml
alias: "Alertă Întrerupere Termoficare"
trigger:
  - platform: state
    entity_id: sensor.cmteb_agent_afectat_STRADA
    to: "ÎNCĂLZIRE"
  - platform: state
    entity_id: sensor.cmteb_agent_afectat_STRADA
    to: "APĂ CALDĂ"
action:
  - service: notify.mobile_app_telefonul_tau
    data:
      title: "⚠️ Întrerupere Termoficare Detectată"
      message: |
        S-a declanșat o întrerupere la termoficare!
        
        📍 Locație: {{ states.sensor.cmteb_agent_afectat_STRADA.attributes.Adresa }}
        🔥 Agent afectat: {{ states.sensor.cmteb_agent_afectat_STRADA.state }}
        🛠️ Cauză: {{ states.sensor.cmteb_cauza_interventie_STRADA.state }}

```
---
## 🛠️ Depanare
🔍 Logging pentru Debug
Adaugă în configuration.yaml:
```yaml
logger:
  default: info
  logs:
    custom_components.cmteb_termoficare: debug
```
---
## ❌ Erori Comune
| Eroare | Cauză | Soluție |
|--------|-----------|----------------|
| `"Connection refused"` | Site-ul CMTEB indisponibil | Așteaptă și reîncearcă |
| `"Nu s-au găsit tabele"` | Structura paginii schimbată | Raportează issue |

---
## 📞 Suport
Dacă ai întrebări sau probleme:
 1. Verifică documentația de mai sus
 2. Caută issues existente pe GitHub
 3. Deschide un nou issue dacă problema nu a fost raportată

🔗 Repository: https://github.com/georgeRPI/cmteb_termoficare

---
## ✨ Făcut cu pasiune pentru comunitatea Home Assistant România ✨
