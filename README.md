# CMTEB Termoficare pentru Home Assistant

Integrare care extrage informații despre întreruperile la termoficare de pe site-ul CMTEB.

## Instalare

### Prin HACS (Recomandat)

1. Deschide HACS în Home Assistant
2. Click pe "Integrări"
3. Click pe butonul cu 3 puncte în colțul dreapta sus
4. Selectează "Repository-uri personalizate"
5. Adaugă URL-ul: `https://github.com/numele_tau_github/cmteb_termoficare`
6. Selectează categoria "Integration"
7. Click pe "Adaugă"
8. Găsește "CMTEB Termoficare" în lista de integrări noi și click "Download"

### Configurare

1. După instalare, repornește Home Assistant
2. Mergi la Settings → Devices & Services → Add Integration
3. Caută "CMTEB Termoficare"
4. Completează:
   - **Nume Locație**: Un nume pentru locația ta (ex: "Acasă")
   - **Adresă**: Adresa exactă cum apare pe site-ul CMTEB

## Senzori

Integrarea creează 3 senzori:
- `sensor.cmteb_agent_afectat` - Agentul termic afectat (ÎNCĂLZIRE/APĂ CALDĂ)
- `sensor.cmteb_cauza_interventie` - Cauza intervenției
- `sensor.cmteb_data_estimata_reparatie` - Data estimată pentru reparatie

## Suport

Dacă întâmpini probleme, creează un issue pe GitHub.
