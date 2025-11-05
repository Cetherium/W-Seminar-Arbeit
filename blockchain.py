import hashlib
import time 
import json

class Block:
    def __init__(self, index, zeitstempel, transaktionen, vorheriger_hash, nonce=0):
        self.index = index
        self.zeitstempel = zeitstempel
        self.transaktionen = transaktionen
        self.vorheriger_hash = vorheriger_hash
        self.nonce = nonce
        self.hash = self.berechne_hash()

    def berechne_hash(self):
        "Eine Methode, die den SHA-256 Hash des Blocks berechnet."

        block_als_dictinary = {
            'index': self.index,
            'zeitstempel': self.zeitstempel,
            'transaktionen': self.transaktionen,
            'vorheriger_hash': self.vorheriger_hash,
            'nonce': self.nonce
        }

        block_als_string = json.dumps(block_als_dictinary, sort_keys=True)
        return hashlib.sha256(block_als_string.encode()).hexdigest()
    
    def block_schürfen(self, schwierigkeit):
        "Eine Methode, die den Proof-of-Work Algorithmus implementiert."

        ziel = '0' * schwierigkeit
        while not self.hash.startswith(ziel):
            self.nonce += 1
            self.hash = self.berechne_hash()

        print(f"Block geschürft: {self.hash} mit Nonce: {self.nonce}")

    def in_dictionary_umwandeln(self):
        "Eine Methode, die den Block in ein Dictionary umwandelt."

        return {
            'index': self.index,
            'zeitstempel': self.zeitstempel,
            'transaktionen': self.transaktionen,
            'vorheriger_hash': self.vorheriger_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }
    

class Blockchain:
    def __init__(self, schwierigkeit=4):
        self.chain = []
        self.mempool = []
        self.schwierigkeit = schwierigkeit
        self.erzeuge_genesis_block()

    def erzeuge_genesis_block(self):
        "Eine Methode, die den Genesis-Block erstellt."

        genesis_block = Block(
            index=0,
            zeitstempel=time.time(),
            transaktionen=[{
                'sender': 'System',
                'empfänger': 'Genesis',
                'betrag': 0
            }],
            vorheriger_hash="0",
            nonce=0,
        )

        self.chain.append(genesis_block)
        print(f"Genesis Block erstellt: {genesis_block.hash[:16]}") # Ausgabe der ersten 16 Zeichen des Hashs

    def hole_letzten_block(self):
        "Eine Methode, die den letzten Block der Blockchain zurückgibt."
        return self.chain[-1]
    
    def füge_transaktion_hinzu(self, transaktion):
        "Eine Methode, die eine Transaktion zum Mempool hinzufügt."
        
        # Ist die Transaktion gültig?
        notwendige_felder = ['sender', 'empfänger', 'betrag']
        if not all(feld in transaktion for feld in notwendige_felder):
            print("Ungültige Transaktion. Fehlende Felder.")
            return False
        
        # ist ein Zeitstempel vorhanden?
        if 'zeitstempel' not in transaktion:
            transaktion['zeitstempel'] = time.time()

        self.mempool.append(transaktion)
        print(f"Transaktion hinzugefügt: {transaktion}")
        return True
    
    def schürfe_offene_transaktionen(self):
        "Eine Methode, die alle offenen Transaktionen im Mempool zu einem neuen Block schürft."

        #Überprüfen, dass Mempool nicht leer ist

        if not self.mempool:
            print("Keine offenen Transaktionen zum Schürfen.")
            return False
        
        print(f"Starte das Schürfen von {len(self.mempool)} Transaktionen...")

        neuer_block = Block(
            index=len(self.chain),
            zeitstempel=time.time(),
            transaktionen=self.mempool.copy(),
            vorheriger_hash=self.hole_letzten_block().hash
        )

        # Schürfen des Blocks
        start_zeit = time.time()
        neuer_block.block_schürfen(self.schwierigkeit)
        end_zeit = time.time()

        schürf_dauer = end_zeit - start_zeit
        print(f"Block geschürft in {schürf_dauer:.2f} Sekunden.") # Ausgabe der Schürfdauer (:.2f für 2 Dezimalstellen)
        self.chain.append(neuer_block)
        print(f"Neuer Block hinzugefügt: {neuer_block.hash[:16]}") # Ausgabe der ersten 16 Zeichen des Hashs
        self.mempool = []  # Leeren des Mempools nach dem Schürfen
        return True
    
    def ist_chain_valide(self):
        "Eine Methode, die überprüft, ob die Blockchain gültig ist."

        for i in range(1, len(self.chain)):
            aktueller_block = self.chain[i]
            vorheriger_block = self.chain[i - 1]

            # Überprüfen des Hashs
            if aktueller_block.hash != aktueller_block.berechne_hash():
                print(f"Ungültiger Hash bei Block {aktueller_block.index}")
                print("Erwartet:", aktueller_block.berechne_hash())
                print("Gefunden:", aktueller_block.hash)
                return False

            # Überprüfen des vorherigen Hashs
            if aktueller_block.vorheriger_hash != vorheriger_block.hash:
                print(f"Ungültiger vorheriger Hash bei Block {aktueller_block.index}")
                return False
            
            # Erfüllt der Block die Schwierigkeit?
            if not aktueller_block.hash.startswith('0' * self.schwierigkeit):
                print(f"Block {aktueller_block.index} erfüllt nicht die Schwierigkeit.")
                return False
            
        return True
    
    def ist_erhaltene_chain_valide(self, erhaltene_chain):
        "Eine Methode, die überprüft, ob eine erhaltene Blockchain gültig ist."

        # Ist die Chain leer?
        if not erhaltene_chain:
            print("Erhaltene Chain ist leer.")
            return False
        

        for i in range(1, len(erhaltene_chain)): # 1, da der Genesis-Block nicht überprüft werden muss
            aktueller_block = erhaltene_chain[i]
            vorheriger_block = erhaltene_chain[i - 1]

            # Überprüfen des Hashs
            if aktueller_block.hash != aktueller_block.berechne_hash():
                print(f"Ungültiger Hash bei Block {aktueller_block.index} in der erhaltenen Chain")
                print("Erwartet:", aktueller_block.berechne_hash())
                print("Gefunden:", aktueller_block.hash)
                return False

            # Überprüfen des vorherigen Hashs
            if aktueller_block.vorheriger_hash != vorheriger_block.hash:
                print(f"Ungültiger vorheriger Hash bei Block {aktueller_block.index} in der erhaltenen Chain")
                return False
            
            # Erfüllt der Block die Schwierigkeit?
            if not aktueller_block.hash.startswith('0' * self.schwierigkeit):
                print(f"Block {aktueller_block.index} in der erhaltenen Chain erfüllt nicht die Schwierigkeit.")
                return False
            
        print("Erhaltene Chain ist gültig.")
        return True
        
    def ersetze_chain(self, neue_chain):
        "Eine Methode, die die aktuelle Chain durch eine neue Chain ersetzt, wenn diese gültig und länger ist."

        if len(neue_chain) <= len(self.chain):
            print("Die neue Chain ist nicht länger als die aktuelle Chain. Ersetzung abgelehnt.")
            return False
        
        if not self.ist_erhaltene_chain_valide(neue_chain):
            print("Die neue Chain ist ungültig. Ersetzung abgelehnt.")
            return False
        
        self.chain = neue_chain
        print("Die aktuelle Chain wurde erfolgreich durch die neue Chain ersetzt.")
        return True
    
    