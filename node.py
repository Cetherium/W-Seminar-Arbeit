from flask import Flask, jsonify, request
from flask_cors import CORS
from blockchain import Blockchain
import requests
import threading
import time

app = Flask(__name__)
CORS(app)

# eigene Blockchain-Instanz erstellen
blockchain = Blockchain()

bekannte_nodes = set()

ORGANISATIONEN = [
    "Rotes Kreuz",
    "WWF",
    "UNICEF",
    "Greenpeace",
    "Ärzte ohne Grenzen"
]

def konsens_logik():

    ersetzt = False
    maximale_lange = len(blockchain.chain)
    neue_chain = None

    print("Starte Konsens-Logik... Aktuelle Kettenlänge:", maximale_lange)

    # Jede bekannte Node abfragen
    for node in bekannte_nodes:
        try:
            print(f"Abfrage der Node {node}...")
            response = requests.get(f'http://{node}/chain', timeout=5) # Anfrage mit Timeout von 5 Sekunden

            if response.status_code == 200:
                daten = response.json()
                erhaltene_chain = daten['chain']
                erhaltene_länge = daten['länge']

                print(f"Peer hat eine Kettenlänge von: {erhaltene_länge} Blöcken")

                print(f"Erhaltene Kettenlänge von {node}: {erhaltene_länge}")

                # Überprüfen, ob die erhaltene Chain länger ist
                if erhaltene_länge > maximale_lange:
                    print("Erhaltene Kette ist länger. Überprüfe Gültigkeit...")

                    # Chain nachbauen und anschließend validieren
                    temporäre_chain = []
                    for block_daten in erhaltene_chain:
                        block = Block(
                            index=block_daten['index'],
                            zeitstempel=block_daten['zeitstempel'],
                            daten=block_daten['daten'],
                            vorheriger_hash=block_daten['vorheriger_hash'],
                            nonce=block_daten['nonce']
                        )
                        block.hash = block_daten['hash']
                        temporäre_chain.append(block)

                    # Valide ?
                    if blockchain.ist_erhaltene_chain_valide(temporäre_chain):
                        maximale_lange = erhaltene_länge
                        neue_chain = temporäre_chain
                        ersetzt = True
                        print("Erhaltene Kette ist gültig und wird übernommen.")
                    else:
                        print("Erhaltene Kette ist ungültig.")

        except requests.exceptions.Timeout:
            print(f"Timeout bei der Anfrage an Node {node}")
        except Exception as e:
            print(f"Fehler bei der Anfrage an Node {node}: {e}")

    if ersetzt:
        blockchain.chain = neue_chain
        print("Die aktuelle Chain wurde durch die neue Chain ersetzt.")
        return {
            'nachricht': "Die aktuelle Chain wurde durch die neue Chain ersetzt.",
            'länge': len(blockchain.chain),
            'ersetzt': True
        }
    else:
        print("Die aktuelle Chain ist die längste. Keine Änderungen vorgenommen.")
        return {
            'nachricht': "Die aktuelle Chain ist die längste. Keine Änderungen vorgenommen.",
            'länge': len(blockchain.chain),
            'ersetzt': False
        }
        
def neue_transaktion_senden(transaktion):
    "Eine Methode, die eine neue Transaktion an alle bekannten Nodes sendet."

    # kennt die Node überhaupt andere Nodes?
    if not bekannte_nodes:
        print("Keine bekannten Nodes vorhanden. Transaktion wird nicht gesendet.")
        return
    
    for node in bekannte_nodes:
        try:
            response = requests.post(
                f"{node}/transactions/receive",
                json=transaktion,
                timeout=5
            )
            if response.status_code == 201:
                print(f"Transaktion erfolgreich an Node {node} gesendet.")
            else:
                print(f"Fehler beim Senden der Transaktion an Node {node}: {response.status_code}")
        except Exception as e:
            print(f"Fehler beim Senden der Transaktion an Node {node}: {e}")

def neuen_block_senden():
    "Eine Methode, die den neu geminten Block an alle bekannten Nodes sendet."

    # kennt die Node überhaupt andere Nodes?
    if not bekannte_nodes:
        print("Keine bekannten Nodes vorhanden. Block wird nicht gesendet.")
        return
    
    for node in bekannte_nodes:
        try:
            response = requests.post(
                f"{node}/blocks/receive",
                json={},
                timeout=5
            )
            if response.status_code == 200:
                print(f"Block-Benachrichtigung an Node {node} gesendet.")
            else:
                print(f"Fehler beim Senden des Blocks an Node {node}: {response.status_code}")
        except Exception as e:
            print(f"Fehler beim Senden des Blocks an Node {node}: {e}")

def automatisch_transaktionen_schürfen_thread():
    "Ein Thread, der automatisch Blöcke schürft, wenn genügend Transaktionen im Mempool sind oder eine bestimmte Zeit vergangen ist."

    print("Automatischer Schürf-Thread gestartet.")

    while True:
        time.sleep(30) # Wartezeit zwischen den Prüfungen

        try:
            # Bedingung 1: Mempool-Größe ist größer als oder gleich 5
            if len(blockchain.mempool) >= 5:
                print("Mempool hat genügend Transaktionen. Starte automatisches Schürfen...")
                blockchain.schürfe_offene_transaktionen()
                neuen_block_senden()
                continue

            # Bedingung 2: Älteste Transaktion ist älter als 2 Minuten
            if blockchain.mempool:
                älteste_transaktion = blockchain.mempool[0]
                alter = time.time() - älteste_transaktion.get('zeitstempel', time.time())

                if alter >= 120: # 2 Minuten
                    print("Automatisches Mining: Transaktionen sind älter als 2 Minuten.")
                    blockchain.schürfe_offene_transaktionen()
                    neuen_block_senden()

        except Exception as e:
            print(f"Fehler im automatischen Schürf-Thread: {e}")

def mit_peer_nodes_synchronisieren_thread():
    "Ein Thread, der die Blockchain regelmäßig mit den Peer-Nodes synchronisiert."

    print("Synchronisations-Thread mit Peer-Nodes gestartet.")

    time.sleep(30)  # Erste Wartezeit vor der ersten Synchronisation

    while True:
        time.sleep(60) # Wartezeit zwischen den Synchronisationen

        try:
            print("Starte Synchronisation mit Peer-Nodes...")
            ergebnis = konsens_logik()
            print(f"Synchronisation abgeschlossen: {ergebnis['nachricht']}")
        except Exception as e:
            print(f"Fehler im Synchronisations-Thread: {e}")



@app.route('/health', methods=['GET'])
def health():
    "Eine Methode, die den Gesundheitszustand der Node zurückgibt"

    return jsonify({
        'status': 'online',
        'blöcke': len(blockchain.chain),
        'offene_transaktionen': len(blockchain.mempool),
        'bekannte_nodes': len(bekannte_nodes),
        'valide': blockchain.ist_chain_valide()
    }, 200)

@app.route('/chain', methods=['GET'])
def chain_ausgeben():
    "Eine Methode, die die gesamte Blockchain zurückgibt"

    chain_daten = [block.in_dictionary_umwandeln() for block in blockchain.chain]
    return jsonify({
        'chain': chain_daten,
        'länge': len(chain_daten)
    }, 200)

@app.route('/organizations', methods=['GET'])
def organisationen_ausgeben():
    "Eine Methode, die die Liste der unterstützten Organisationen zurückgibt."

    return jsonify({
        'organisationen': ORGANISATIONEN
    }, 200)

@app.route('/transactions/new', methods=['POST'])
def neue_transaktion():
    "Eine Methode, die eine neue Transaktion entgegennimmt und hinzufügt."

    data = request.get_json()
    
    # Validierung

    erforderliche_felder = ['sender', 'empfänger', 'betrag']
    if not all(feld in data for feld in erforderliche_felder):
        return jsonify({'nachricht': 'Ungültige Transaktion. Fehlende Felder.'}, 400)

    # Ist Betrag positiv?
    try:
        betrag = float(data['betrag'])
        if betrag <= 0:
            return jsonify({'nachricht': 'Der Betrag muss positiv sein.'}, 400)
    except ValueError:
        return jsonify({'nachricht': 'Der Betrag muss eine Zahl sein.'}, 400)
    
    transaktion = {
        'sender': data['sender'] if data['sender'] else "Anoymer Spender",
        'empfänger': data['empfänger'],
        'betrag': betrag,
        'zeitstempel': time.time()
    }

    blockchain.füge_transaktion_hinzu(transaktion)

    neue_transaktion_senden(transaktion)
    print(f"Neue Transaktion erstellt: {transaktion['sender']} --> {transaktion['empfänger']} : {transaktion['betrag']}")

    return jsonify({
        'nachricht': 'Transaktion erfolgreich hinzugefügt.',
        'transaktion': transaktion
    }), 201

@app.route('/transactions/receive', methods=['POST'])
def empfange_transaktion():
    "Eine Methode, die eine empfangene Transaktion von einer anderen Node verarbeitet."
    
    data = request.get_json()

    erforderliche_felder = ['sender', 'empfänger', 'betrag']
    if not all(feld in data for feld in erforderliche_felder):
        return jsonify({'nachricht': 'Ungültige Transaktion. Fehlende Felder.'}, 400)

    # Duplikate vermeiden

    for transaktion in blockchain.mempool:
        if (transaktion['sender'] == data['sender'] and
            transaktion['empfänger'] == data['empfänger'] and
            transaktion['betrag'] == data['betrag'] and
            abs(transaktion['zeitstempel'] - data['zeitstempel']) < 1):

            print(f"Duplikat-Transaktion ignoriert")
            return jsonify({'nachricht': 'Duplikat-Transaktion ignoriert.'}, 200)
        
    blockchain.füge_transaktion_hinzu(data)
    print(f"Empfangene Transaktion hinzugefügt: {data['sender']} --> {data['empfänger']} : {data['betrag']}")

    return jsonify({'nachricht': 'Transaktion erfolgreich empfangen und hinzugefügt.'}, 201)

@app.route('/mine', methods=['POST'])
def manueller_schürf_start():
    "Eine Methode, die das Schürfen manuell startet."
    
    # sind Transaktionen im Mempool?
    if not blockchain.mempool:
        return jsonify({'nachricht': 'Keine offenen Transaktionen zum Schürfen.'}, 400)
    
    print("Manuelles Schürfen gestartet")
    neuer_block = blockchain.schürfe_offene_transaktionen()
    neuen_block_senden()

    return jsonify({
        'nachricht': 'Neuer Block erfolgreich geschürft.',
        'block': neuer_block.in_dictionary_umwandeln()
    }), 200

@app.route('/blocks/receive', methods=['POST'])
def empfange_block_benachrichtigung():
    "Eine Methode, die eine Benachrichtigung über einen neuen Block von einer anderen Node verarbeitet."

    print("Empfangene Block-Benachrichtigung von Peer-Node.")
    ergebnis = konsens_logik()

    return jsonify(ergebnis), 200


@app.route('/consensus', methods=['POST'])
def konsens_starten():
    "Eine Methode, die die Konsens-Logik manuell auslöst."
    print("Manueller Konsens-Start ausgelöst.")
    ergebnis = konsens_logik()

    return jsonify(ergebnis), 200

@app.route('/nodes/register', methods=['POST'])
def node_registrieren():
    "Eine Methode, die eine neue Node registriert."

    data = request.get_json()

    if not data or 'node_address' not in data:
        return jsonify({'nachricht': 'Ungültige Anfrage. Keine Node-Adresse angegeben.'}, 400)
    
    node_addresse = data['node_address']
    if not node_addresse.startswith('http://'):
        return jsonify({'nachricht': 'Ungültige Node-Adresse. Muss mit http:// beginnen.'}, 400)
    
    bekannte_nodes.add(node_addresse)
    print(f"Neue Node registriert: {node_addresse}")

    return jsonify({
        'nachricht': 'Node erfolgreich registriert.',
        'gesamtanzahl_nodes': len(bekannte_nodes),
        'bekannte_nodes': list(bekannte_nodes)}), 201

@app.route('/nodes/list', methods=['GET'])
def liste_bekannte_nodes():
    "Eine Methode, die die Liste der bekannten Nodes zurückgibt."

    return jsonify({
        'bekannte_nodes': list(bekannte_nodes),
        'gesamtanzahl_nodes': len(bekannte_nodes)
    }), 200

@app.route('/stats', methods=['GET'])
def node_statistiken():
    "Eine Methode, die Statistiken über die Node zurückgibt."

    gesamt_transaktionen = 0.0
    transaktionen_pro_organisation = {org: 0.0 for org in ORGANISATIONEN}

    # Durch Blöcke iterrieren
    for block in blockchain.chain[1:]: # [1:] Genesis-Block überspringen
        for transaktion in block.transaktionen:
            betrag = float(transaktion['betrag'])
            gesamt_transaktionen += betrag

            empfänger = transaktion['empfänger']
            if empfänger in transaktionen_pro_organisation:
                transaktionen_pro_organisation[empfänger] += betrag

    return jsonify({
        'gesamt_transaktionen': gesamt_transaktionen,
        'transaktionen_pro_organisation': transaktionen_pro_organisation,
        'anzahl_blöcke': len(blockchain.chain),
        'anzahl_offene_transaktionen': len(blockchain.mempool),
        'chain_valide': blockchain.ist_chain_valide()
    }), 200

if __name__ == '__main__':
    # Starte Threads für automatisches Schürfen und Synchronisation
    schürf_thread = threading.Thread(target=automatisch_transaktionen_schürfen_thread, daemon=True)
    schürf_thread.start()
    sync_thread = threading.Thread(target=mit_peer_nodes_synchronisieren_thread, daemon=True)
    sync_thread.start()

    print("Starte Flask-Server auf Port 5000...")
    print("Blockchain-Node ist online.")
    print("Genesis Block Hash:", blockchain.chain[0].hash[:16]) # Ausgabe der ersten 16 Zeichen des Hashs
    app.run(host='0.0.0.0', port=5000, debug=False)