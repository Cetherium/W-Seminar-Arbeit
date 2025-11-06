const NODES = [
    'http://72.61.185.109:5000',  // VPS 1
    'http://72.61.185.115:5000',  // VPS 2
];

let aktuelleNodeIndex = 0;
let organisationen = [];
let updateIntervall;


function aktuellenNodeholen() {
    return NODES[aktuelleNodeIndex];
}

// Wechsle zu der nächsten Node in der Liste
function zurNaechstenNodeWechseln() {
    aktuelleNodeIndex = (aktuelleNodeIndex + 1) % NODES.length;
}

// API Request -> Wenn scheitert -> Nächste Node versuchen
async function apiRequest(endpoint, options = {}) {
    for (let versuch = 0; versuch < NODES.length; versuch++) {
        try {
            const node = aktuellenNodeholen();
            const response = await fetch(`${node}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`Fehlerhafte Antwort von Node: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Fehler bei der Anfrage an Node ${aktuellenNodeholen()}:`, error);
            zurNaechstenNodeWechseln();

            if (versuch === NODES.length - 1) {
                throw new Error('Alle Nodes sind nicht erreichbar.');
            }
        }
        
    }
        
    
}

function showToast(nachricht, type = 'success') {
    const container = document.querySelector('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = nachricht;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function datumFormatieren(datumString) {
    const datum = new Date(datumString * 1000);
    return datum.toLocaleDateString('de-DE');
}


async function updateNodeStatus() {
    for (let i = 0; i < NODES.length; i++) {
        const statusElement = document.querySelector(`#node-status-${i + 1}-status`);
        const indikator = document.querySelector('.node-indikator');
        const blocksElement = statusElement.querySelector('.node-blocks');

        try {
            const response = await fetch(`${NODES[i]}/health`, { timeout: 5000 });
            const data = await response.json();

            indikator.classList.remove('offline');
            indikator.classList.add('online');
            blocksElement.textContent =  `${data.blocks} Blöcke`
        } catch (error) {
            indikator.classList.remove('online');
            indikator.classList.add('offline');
            blocksElement.textContent = 'Offline';
        }
        
    }
}


async function ladeOrganisationen() {
    try {
        const data = await apiRequest('/organisations');
        organisationen = data.organisations;
        const select = document.querySelector('#organisation-select');
        select.innerHTML = '<option value="">-- Bitte wählen --</option>';

        organisationen.forEach(organisation => {
            const option = document.createElement('option');
            option.value = organisation;
            option.textContent = organisation;
            select.appendChild(option);
        })
    } catch (error) {
        console.error('Fehler beim Laden der Organisationen:', error);
        showToast('Fehler beim Laden der Organisationen.', 'error');
    }
}


async function TransaktionAbsenden(event) {
    event.preventDefault();

    const sender = document.getElementById('sender').value || 'Anonymer Spender';
    const empfänger = document.getElementById('organization').value;
    const betrag = parseFloat(document.getElementById('betrag').value);

    if (!empfänger) {
        showToast('Bitte geben Sie einen Empfänger an.', 'error');
        return;
    }

    if (!betrag || betrag <= 0) {
        showToast('Bitte geben Sie einen gültigen Betrag an.', 'error');
        return;
    }

    const spendenKnopf = document.getElementById('donate-btn')
    spendenKnopf.disabled = true;
    spendenKnopf.textContent = 'Wird gesendet...';

    try {
        await apiRequest('/transactions/new', {
            method: 'POST',
            body: JSON.stringify({
                sender: sender,
                empfänger: empfänger,
                betrag: betrag
            })
        });

        showToast('Spende erfolgreich gesendet!', 'success');
        document.getElementById('betrag').value = '';
        document.getElementById('organization').value = '';
    } catch (error) {
        console.error('Fehler beim Spenden:', error);
        showToast('Spende fehlgeschlagen. Versuche es erneut.', 'error');
    } finally {
        spendenKnopf.disabled = false;
        spendenKnopf.textContent = 'Spenden';
    }
}

async function ladeStatistiken() {
    try {
        const data = await apiRequest('/stats');

        document.querySelector('#total-donations-quick').textContent = `${data.gesamt_transaktionen} €`;
        document.querySelector('#total-blocks-quick').textContent = data.anzahl_blöcke;
        document.querySelector('#pending-transactions-quick').textContent = data.anzahl_offene_transaktionen;

        const validBadge = document.querySelector('#chain-valid-badge');
        if (data.chain_valide) {
            validBadge.innerHTML = '<span class="status-badge valid">✓ Gültig</span>';
        } else {
            validBadge.innerHTML = '<span class="status-badge invalid">✗ Ungültig</span>';
        }

        const organisationListe = document.querySelector('#org-list');
        organisationListe.innerHTML = '';
        const sortierteOrganisationen = Object.entries(data.transaktionen_pro_organisation)
            .sort((a, b) => b[1] - a[1]);

        sortierteOrganisationen.forEach(([organisation, anzahl]) => {
            const item = document.createElement('div');
            item.className = 'org-item';
            item.innerHTML = `
                <span class="org-name">${organisation}</span>
                <span class="org-transactions">${anzahl} Spenden</span>
            `;
            organisationListe.appendChild(item);
        });
    } catch (error) {
        console.error('Fehler beim Laden der Statistiken:', error);
    }
}

async function ladeNeueTransaktionen() {
    try {
        const data = await apiRequest('/chain');
        const chain = data.chain;

        const container = document.querySelector('#recent-transactions');

        let alleTransaktionen = [];
        for (let i = 0; i < chain.length; i++) {
            const block = chain[i];
            block.transaktionen.forEach(transaktion => {
                alleTransaktionen.push({
                    ...transaktion,
                    blockIndex: block.index,
                    zeitspempel: block.zeitstempel
                });
            });
        }

        // Hier können Sie die gesammelten Transaktionen anzeigen
        alleTransaktionen.reverse();

        const letzteTransaktionen = alleTransaktionen.slice(0, 10);
        if(letzteTransaktionen.length === 0) {
            container.innerHTML = '<p>Keine Transaktionen gefunden.</p>';
            return;
        }

        container.innerHTML = '<div class="transaction-list"></div>';
        const list = container.querySelector('.transaction-list');

        letzteTransaktionen.forEach(transaktion => {
            const item = document.createElement('div');
             item.className = 'transaction-item';
             item.innerHTML = `
                <div class="transaction-info">
                    <span class="transaction-sender">${transaktion.sender}</span>
                    <span class="transaction-recipient">→ ${transaktion.empfänger}</span>
                </div>
                <span class="transaction-amount">${transaktion.betrag} €</span>
            `;
            list.appendChild(item);
        })
    } catch (error) {
        console.error('Fehler beim Laden der Transaktionen:', error);
    }

}


async function ladeBlockchain() {
    try {
        const data = await apiRequest('/chain');
        const chain = data.chain;

        const container = document.querySelector('#blockchain-view');

        if (chain.length === 0) {
            container.innerHTML = '<p class="loading">Keine Blöcke vorhanden</p>';
            return;
        }

        container.innerHTML = '<div class="block-list"></div>';
        const list = container.querySelector('.block-list');
        
        // Neueste Blöcke zuerst
        const reversedChain = [...chain].reverse();

        reversedChain.forEach(block => {
            const item = document.createElement('div');
            item.className = 'block-item';

            const txCount = block.transaktionen.length;
            const time = datumFormatieren(block.zeitstempel);
            
            item.innerHTML = `
                <div class="block-header">
                    <span class="block-index">Block #${block.index}</span>
                    <span class="block-time">${time}</span>
                </div>
                <div class="block-hash">
                    <strong>Hash:</strong> ${block.hash}
                </div>
                <div class="block-hash">
                    <strong>Previous:</strong> ${block.previous_hash}
                </div>
                <div class="block-transactions">
                    <strong>Transaktionen:</strong> ${txCount} | <strong>Nonce:</strong> ${block.nonce}
                </div>
            `;
            list.appendChild(item);
        });

}catch (error) {
        console.error('Fehler beim Laden der Blockchain:', error);
        document.getElementById('blockchain-view').innerHTML = 
            '<p class="loading">Fehler beim Laden der Blockchain</p>';
    }
}

async function syncNodes() {
    const btn = document.getElementById('sync-nodes');
    const msg = document.getElementById('admin-message');
    
    btn.disabled = true;
    btn.textContent = '⏳ Synchronisiere...';
    
    try {
        // Registriere Nodes gegenseitig
        await fetch(`${NODES[0]}/nodes/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_address: NODES[1] })
        });
        
        await fetch(`${NODES[1]}/nodes/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_address: NODES[0] })
        });
        
        msg.className = 'message success';
        msg.textContent = '✅ Nodes erfolgreich synchronisiert!';
        showToast('Nodes synchronisiert', 'success');
        
    } catch (error) {
        msg.className = 'message error';
        msg.textContent = '❌ Synchronisierung fehlgeschlagen';
        showToast('Synchronisierung fehlgeschlagen', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔄 Nodes synchronisieren';
    }
}

async function manualMine() {
    const btn = document.getElementById('manual-mine');
    const msg = document.getElementById('admin-message');
    
    btn.disabled = true;
    btn.textContent = '⏳ Mining...';
    
    try {
        await apiRequest('/mine', { method: 'POST' });
        
        msg.className = 'message success';
        msg.textContent = '✅ Block erfolgreich gemined!';
        showToast('Block gemined!', 'success');
        
        // Daten aktualisieren
        setTimeout(() => {
            loadStatistics();
            loadBlockchain();
            loadRecentTransactions();
            updateNodeStatus();
        }, 2000);
        
    } catch (error) {
        msg.className = 'message error';
        msg.textContent = '❌ Mining fehlgeschlagen. Keine Transaktionen vorhanden?';
        showToast('Mining fehlgeschlagen', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '⛏️ Manuell minen';
    }
}

async function runConsensus() {
    const btn = document.getElementById('run-consensus');
    const msg = document.getElementById('admin-message');
    
    btn.disabled = true;
    btn.textContent = '⏳ Konsens läuft...';
    
    try {
        // Konsens auf beiden Nodes starten
        await Promise.all([
            fetch(`${NODES[0]}/consensus`, { method: 'POST' }),
            fetch(`${NODES[1]}/consensus`, { method: 'POST' })
        ]);
        
        msg.className = 'message success';
        msg.textContent = '✅ Konsens erfolgreich durchgeführt!';
        showToast('Konsens durchgeführt', 'success');
        
        // Daten aktualisieren
        setTimeout(() => {
            loadStatistics();
            loadBlockchain();
            updateNodeStatus();
        }, 1000);
        
    } catch (error) {
        msg.className = 'message error';
        msg.textContent = '❌ Konsens fehlgeschlagen';
        showToast('Konsens fehlgeschlagen', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🤝 Konsens starten';
    }
}

// ==================== INITIALIZATION ====================

async function initializeApp() {
    console.log('🚀 Blockchain Donation Platform wird gestartet...');
    console.log('Nodes:', NODES);
    
    // Event Listeners
    document.getElementById('donation-form').addEventListener('submit', TransaktionAbsenden);
    document.getElementById('refresh-stats').addEventListener('click', ladeStatistiken);
    document.getElementById('refresh-chain').addEventListener('click', ladeBlockchain);
    document.getElementById('sync-nodes').addEventListener('click', syncNodes);
    document.getElementById('manual-mine').addEventListener('click', manualMine);
    document.getElementById('run-consensus').addEventListener('click', runConsensus);

    // Initial laden
    await ladeOrganisationen();
    await updateNodeStatus();
    await ladeStatistiken();
    await ladeNeueTransaktionen();
    await ladeBlockchain();
    
    // Auto-Update alle 10 Sekunden
    updateIntervall = setInterval(async () => {
        await updateNodeStatus();
        await ladeStatistiken();
        await ladeNeueTransaktionen();
    }, 10000);
    
    console.log('✅ App erfolgreich initialisiert!');
}

// App starten wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', initializeApp);

// Cleanup beim Verlassen der Seite
window.addEventListener('beforeunload', () => {
    if (updateIntervall) {
        clearInterval(updateIntervall);
    }
});