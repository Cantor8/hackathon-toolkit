"""Canton Resilient Scanner & Humanitarian Field Portal Server.

Stdlib-only Python HTTP Server providing:
- Full REST API for Canton Scanner, Medical Stock, and EHR Records.
- WHO ICD-11 / SNOMED-CT clinical coding, Bloods Lab Panel & Encrypted Media.
- Real-time Interactive Web Dashboard (Glassmorphic UI, Mobile/Desktop responsive).
- Live Drift Injection & Automated Healing Controls for judging demos.
- Low-Data / Edge-Mesh conservation mode toggle.
"""

import http.server
import json
import logging
import os
import socketserver
import sys
import threading
import time
import urllib.parse

from c8_scanner import CantonScanner
from c8_drift_sentinel import DriftSentinel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("C8Server")

PORT = int(os.environ.get("PORT", 8088))

scanner = CantonScanner()
sentinel = DriftSentinel(scanner)

HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IronFlower | Resilient Canton Scanner & Humanitarian Field Portal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#f0fdfa', 500: '#14b8a6', 600: '#0d9488', 900: '#134e4a' },
            darkbg: '#080c14',
            cardbg: '#111827',
            cardborder: '#1f2937'
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #080c14; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .glass { background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .pulse-dot { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .4; transform: scale(1.15); } }
  </style>
</head>
<body class="text-slate-100 min-h-screen">
  <!-- Header -->
  <header class="border-b border-gray-800 bg-gray-900/70 sticky top-0 z-50 backdrop-blur-md">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400 font-bold">
          <i class="fa-solid fa-spa text-lg text-emerald-400"></i>
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300 bg-clip-text text-transparent">IronFlower</h1>
          <p class="text-xs text-gray-400">Tekkadan Protocol | Resilient Canton Medical Mesh & Clinical Sentinel</p>
        </div>
      </div>
      
      <!-- Status Badges -->
      <div class="flex items-center space-x-3">
        <div class="flex items-center space-x-2 bg-teal-950/40 border border-teal-800/40 px-3 py-1 rounded-full text-xs font-medium text-teal-400">
          <span class="w-2 h-2 rounded-full bg-teal-400 pulse-dot"></span>
          <span>Ledger Offset: <strong id="header-offset">100</strong></span>
        </div>
        <button id="low-data-btn" onclick="toggleLowData()" class="flex items-center space-x-1 bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1 rounded-full text-xs text-gray-300 transition">
          <i class="fa-solid fa-tower-broadcast text-yellow-400"></i>
          <span id="low-data-label">Low-Data: OFF</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    
    <!-- Top Metrics Overview -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <div class="glass p-4 rounded-xl">
        <p class="text-xs text-gray-400 font-medium">Active Contracts (ACS)</p>
        <h3 id="stat-contracts" class="text-2xl font-extrabold text-teal-400 mt-1">4</h3>
        <p class="text-[11px] text-gray-500 mt-1">Indexed via InterfaceFilter</p>
      </div>
      <div class="glass p-4 rounded-xl">
        <p class="text-xs text-gray-400 font-medium">Transactions Processed</p>
        <h3 id="stat-txs" class="text-2xl font-extrabold text-cyan-400 mt-1">2</h3>
        <p class="text-[11px] text-gray-500 mt-1">0 lost on crash recovery</p>
      </div>
      <div class="glass p-4 rounded-xl">
        <p class="text-xs text-gray-400 font-medium">Drift Invariants</p>
        <h3 id="stat-drift" class="text-2xl font-extrabold text-emerald-400 mt-1">0 Drift</h3>
        <p class="text-[11px] text-emerald-500/80 mt-1"><i class="fa-solid fa-check-circle"></i> 100% In Sync</p>
      </div>
      <div class="glass p-4 rounded-xl">
        <p class="text-xs text-gray-400 font-medium">Bandwidth Saved</p>
        <h3 id="stat-savings" class="text-2xl font-extrabold text-purple-400 mt-1">148.2 KB</h3>
        <p class="text-[11px] text-purple-400/80 mt-1">Edge compression active</p>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex space-x-2 border-b border-gray-800 mb-6 overflow-x-auto">
      <button onclick="switchTab('inventory')" id="tab-inventory" class="tab-btn px-4 py-2.5 text-sm font-semibold text-teal-400 border-b-2 border-teal-400 flex items-center space-x-2 whitespace-nowrap">
        <i class="fa-solid fa-boxes-stacked"></i><span>Medical Stock & Escrow</span>
      </button>
      <button onclick="switchTab('patients')" id="tab-patients" class="tab-btn px-4 py-2.5 text-sm font-medium text-gray-400 hover:text-gray-200 flex items-center space-x-2 whitespace-nowrap">
        <i class="fa-solid fa-notes-medical"></i><span>WHO Clinical EHR & Triage</span>
      </button>
      <button onclick="switchTab('scanner')" id="tab-scanner" class="tab-btn px-4 py-2.5 text-sm font-medium text-gray-400 hover:text-gray-200 flex items-center space-x-2 whitespace-nowrap">
        <i class="fa-solid fa-satellite-dish"></i><span>Canton Scanner & Balances</span>
      </button>
      <button onclick="switchTab('resilience')" id="tab-resilience" class="tab-btn px-4 py-2.5 text-sm font-medium text-gray-400 hover:text-gray-200 flex items-center space-x-2 whitespace-nowrap">
        <i class="fa-solid fa-shield-virus"></i><span>Drift Sentinel & Fault Lab</span>
      </button>
    </div>

    <!-- Tab 1: Medical Inventory & Escrow -->
    <div id="view-inventory" class="tab-view space-y-6">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 class="text-base font-semibold text-white">Frontline Medical Supplies & Cold-Chain Tracking</h2>
          <p class="text-xs text-gray-400">Verifiable stock in contested corridors protected by Canton sub-transaction privacy.</p>
        </div>
        <button onclick="simulateDelivery()" class="bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 text-white font-medium text-xs px-3.5 py-2 rounded-lg shadow-lg flex items-center space-x-2">
          <i class="fa-solid fa-truck-ramp-box"></i><span>Simulate Atomic DvP Delivery</span>
        </button>
      </div>

      <div class="glass rounded-xl overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-gray-300">
            <thead class="bg-gray-900/80 text-gray-400 uppercase tracking-wider text-[11px] border-b border-gray-800">
              <tr>
                <th class="px-4 py-3">Item / Batch</th>
                <th class="px-4 py-3">Category</th>
                <th class="px-4 py-3">Stock Qty</th>
                <th class="px-4 py-3">Location</th>
                <th class="px-4 py-3">Custodian Party</th>
                <th class="px-4 py-3">Cold-Chain Status</th>
              </tr>
            </thead>
            <tbody id="inventory-table" class="divide-y divide-gray-800/60">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 2: WHO Clinical EHR & Triage -->
    <div id="view-patients" class="tab-view hidden space-y-6">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 class="text-base font-semibold text-white">Anonymous Frontline EHR Triage & Clinical Coding</h2>
          <p class="text-xs text-gray-400">WHO ICD-11 & SNOMED-CT coded clinical encounters with cryptographic audit roots & bloods.</p>
        </div>
        <button onclick="openNewEncounterModal()" class="bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs px-3.5 py-2 rounded-lg shadow flex items-center space-x-2">
          <i class="fa-solid fa-plus-circle"></i><span>Record New Triage Encounter</span>
        </button>
      </div>

      <!-- Triage Cards Grid -->
      <div id="patients-cards" class="space-y-4">
        <!-- Rendered via JS -->
      </div>
    </div>

    <!-- Tab 3: Canton Scanner & Balances -->
    <div id="view-scanner" class="tab-view hidden space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Party Holdings -->
        <div class="glass rounded-xl p-5 space-y-4">
          <div class="flex justify-between items-center border-b border-gray-800 pb-3">
            <h3 class="text-sm font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-wallet text-teal-400"></i><span>Active Party Balances (ACS)</span>
            </h3>
            <span class="text-[11px] text-gray-400">InterfaceFilter: Splice.Holding</span>
          </div>
          <div id="balances-list" class="space-y-3">
            <!-- Rendered via JS -->
          </div>
        </div>

        <!-- Transfer History -->
        <div class="glass rounded-xl p-5 space-y-4">
          <div class="flex justify-between items-center border-b border-gray-800 pb-3">
            <h3 class="text-sm font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-arrow-right-arrow-left text-cyan-400"></i><span>Live Canton Transfer Stream</span>
            </h3>
            <span class="text-[11px] text-teal-400 font-mono">Offset: <span id="stream-offset">100</span></span>
          </div>
          <div id="transfers-list" class="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
            <!-- Rendered via JS -->
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 4: Drift Sentinel & Fault Lab -->
    <div id="view-resilience" class="tab-view hidden space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Node Multi-Failover Status -->
        <div class="glass rounded-xl p-5 space-y-4">
          <h3 class="text-sm font-bold text-white flex items-center space-x-2">
            <i class="fa-solid fa-network-wired text-purple-400"></i><span>Node Multi-Cluster Health</span>
          </h3>
          <div class="space-y-3" id="nodes-list">
            <!-- Rendered via JS -->
          </div>
        </div>

        <!-- Drift Attack Controls (For Hackathon Judges) -->
        <div class="glass rounded-xl p-5 space-y-4 lg:col-span-2">
          <div class="flex justify-between items-center border-b border-gray-800 pb-3">
            <div>
              <h3 class="text-sm font-bold text-white flex items-center space-x-2">
                <i class="fa-solid fa-bug text-rose-400"></i><span>Track A2: Drift Sentinel & Invariant Tester</span>
              </h3>
              <p class="text-xs text-gray-400 mt-0.5">Inject deliberate state drift to demo automated detection & reconciliation live for judges.</p>
            </div>
            <button onclick="autoRepairDrift()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition flex items-center space-x-1.5">
              <i class="fa-solid fa-wrench"></i><span>Trigger Auto-Reconcile</span>
            </button>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <button onclick="injectDrift('STUCK_SUBMISSION')" class="bg-rose-950/30 hover:bg-rose-900/40 border border-rose-800/40 text-rose-300 p-3 rounded-lg text-left transition">
              <div class="font-bold text-xs flex items-center space-x-1.5">
                <i class="fa-solid fa-triangle-exclamation"></i><span>1. Inject Stuck Ghost Contract</span>
              </div>
              <p class="text-[11px] text-rose-400/70 mt-1">Simulates uncommitted holding (-500 Amulet)</p>
            </button>

            <button onclick="injectDrift('TAMPERED_INVENTORY')" class="bg-amber-950/30 hover:bg-amber-900/40 border border-amber-800/40 text-amber-300 p-3 rounded-lg text-left transition">
              <div class="font-bold text-xs flex items-center space-x-1.5">
                <i class="fa-solid fa-boxes-packing"></i><span>2. Inject Tampered Inventory</span>
              </div>
              <p class="text-[11px] text-amber-400/70 mt-1">Forces negative stock invariant breach</p>
            </button>

            <button onclick="injectDrift('SPOOFED_AUTHORIZATION')" class="bg-purple-950/30 hover:bg-purple-900/40 border border-purple-800/40 text-purple-300 p-3 rounded-lg text-left transition">
              <div class="font-bold text-xs flex items-center space-x-1.5">
                <i class="fa-solid fa-user-ninja"></i><span>3. Inject Spoofed Signature</span>
              </div>
              <p class="text-[11px] text-purple-400/70 mt-1">Simulates forged party without CanActAs</p>
            </button>

            <button onclick="injectDrift('REPLAY_CONTRACT_CALL')" class="bg-cyan-950/30 hover:bg-cyan-900/40 border border-cyan-800/40 text-cyan-300 p-3 rounded-lg text-left transition">
              <div class="font-bold text-xs flex items-center space-x-1.5">
                <i class="fa-solid fa-copy"></i><span>4. Inject Replay Contract Call</span>
              </div>
              <p class="text-[11px] text-cyan-400/70 mt-1">Simulates copying an archived choice</p>
            </button>
          </div>

          <!-- Zero-Trust Architecture Security Guardrails Card -->
          <div class="bg-gray-900/70 border border-teal-500/20 rounded-lg p-3.5 space-y-2">
            <h4 class="text-xs font-bold text-teal-300 flex items-center space-x-1.5">
              <i class="fa-solid fa-shield-halved"></i><span>Zero-Trust Authorization & Anti-Spoofing Architecture (OAuth / ZAF)</span>
            </h4>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-gray-300">
              <div class="bg-gray-800/50 p-2 rounded border border-gray-700/50">
                <strong class="text-white block"><i class="fa-solid fa-fingerprint text-teal-400 mr-1"></i>Non-Spoofable Parties</strong>
                Party IDs use cryptographic multihashes (<code>Party::1220...</code>). Impossible to forge without private key.
              </div>
              <div class="bg-gray-800/50 p-2 rounded border border-gray-700/50">
                <strong class="text-white block"><i class="fa-solid fa-ban text-rose-400 mr-1"></i>Anti-Replay Nonces</strong>
                Daml choices archive UTXOs upon execution. Nonces prevent copied transaction execution.
              </div>
              <div class="bg-gray-800/50 p-2 rounded border border-gray-700/50">
                <strong class="text-white block"><i class="fa-solid fa-key text-yellow-400 mr-1"></i>Keycloak OAuth + CanActAs</strong>
                OAuth 2.0 authenticates identity; Canton <code>CanActAs</code> rights strictly govern authorization.
              </div>
            </div>
          </div>

          <!-- Audit Log -->
          <div class="space-y-2">
            <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Drift Detection & Repair Audit Log</h4>
            <div id="drift-log" class="max-h-48 overflow-y-auto space-y-2 text-xs">
              <!-- Rendered via JS -->
            </div>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- Modal for New Clinical Triage Encounter -->
  <div id="encounter-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="glass max-w-xl w-full rounded-2xl p-6 space-y-4 border border-teal-500/30 shadow-2xl">
      <div class="flex justify-between items-center border-b border-gray-800 pb-3">
        <h3 class="text-base font-bold text-white flex items-center space-x-2">
          <i class="fa-solid fa-notes-medical text-teal-400"></i><span>New Frontline Triage Encounter</span>
        </h3>
        <button onclick="closeNewEncounterModal()" class="text-gray-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <form id="encounter-form" onsubmit="submitNewEncounter(event)" class="space-y-3 text-xs">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-gray-400 mb-1">Triage Priority</label>
            <select id="form-triage" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-white">
              <option value="Red (Immediate)">Red (Immediate - Resuscitation)</option>
              <option value="Yellow (Delayed)">Yellow (Delayed - Urgent)</option>
              <option value="Green (Minimal)">Green (Minimal - Ambulatory)</option>
            </select>
          </div>
          <div>
            <label class="block text-gray-400 mb-1">Treating Facility</label>
            <input type="text" id="form-facility" value="Underground Surgical Unit 04" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-white" />
          </div>
        </div>

        <div>
          <label class="block text-gray-400 mb-1">Clinical Diagnosis & Presentation</label>
          <input type="text" id="form-condition" value="Penetrating chest shrapnel with tension pneumothorax" required class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-white" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-gray-400 mb-1">WHO ICD-11 Code</label>
            <input type="text" id="form-icd11" value="ICD-11: NB30 (Traumatic pneumothorax)" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-teal-300 font-mono" />
          </div>
          <div>
            <label class="block text-gray-400 mb-1">SNOMED-CT Concept</label>
            <input type="text" id="form-snomed" value="SNOMED-CT: 81898007 (Pneumothorax)" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-cyan-300 font-mono" />
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2">
          <div>
            <label class="block text-gray-400 mb-1">Blood Type</label>
            <input type="text" id="form-blood-type" value="O-Neg Universal" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-1.5 text-white" />
          </div>
          <div>
            <label class="block text-gray-400 mb-1">Hb (g/dL)</label>
            <input type="number" step="0.1" id="form-hb" value="7.1" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-1.5 text-white" />
          </div>
          <div>
            <label class="block text-gray-400 mb-1">Lactate (mmol/L)</label>
            <input type="number" step="0.1" id="form-lactate" value="4.2" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-1.5 text-white" />
          </div>
        </div>

        <div>
          <label class="block text-gray-400 mb-1">Allocated Supplies (Triggers Canton Escrow)</label>
          <input type="text" id="form-supplies" value="1x Chest Tube Kit, 2x Lyophilized Plasma, 1x Anesthesia Ampoule" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-amber-300" />
        </div>

        <div>
          <label class="block text-gray-400 mb-1">Medic Voice Dictation / Procedure Transcript</label>
          <textarea id="form-notes" rows="2" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-gray-200">DICTATED NOTE: Needle decompression performed at 2nd intercostal space. Chest tube inserted with 400ml hemothorax drainage. Plasma infusion initiated. Canton escrow tx verified.</textarea>
        </div>

        <div class="flex justify-end space-x-2 pt-2 border-t border-gray-800">
          <button type="button" onclick="closeNewEncounterModal()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 font-medium">Cancel</button>
          <button type="submit" class="px-4 py-2 bg-teal-600 hover:bg-teal-500 rounded-lg text-white font-bold flex items-center space-x-1.5">
            <i class="fa-solid fa-fingerprint"></i><span>Sign & Commit to Canton</span>
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- JavaScript logic -->
  <script>
    let lowDataActive = false;

    function switchTab(tabId) {
      document.querySelectorAll('.tab-view').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('text-teal-400', 'border-b-2', 'border-teal-400');
        el.classList.add('text-gray-400');
      });
      document.getElementById('view-' + tabId).classList.remove('hidden');
      const btn = document.getElementById('tab-' + tabId);
      btn.classList.add('text-teal-400', 'border-b-2', 'border-teal-400');
      btn.classList.remove('text-gray-400');
    }

    function openNewEncounterModal() {
      document.getElementById('encounter-modal').classList.remove('hidden');
    }

    function closeNewEncounterModal() {
      document.getElementById('encounter-modal').classList.add('hidden');
    }

    async function toggleLowData() {
      const res = await fetch('/api/settings/low-data', { method: 'POST' });
      const data = await res.json();
      lowDataActive = data.low_data_mode;
      document.getElementById('low-data-label').innerText = 'Low-Data: ' + (lowDataActive ? 'ON (Edge Mesh)' : 'OFF');
      document.getElementById('low-data-btn').className = lowDataActive 
        ? 'flex items-center space-x-1 bg-yellow-950/60 border border-yellow-700/60 px-3 py-1 rounded-full text-xs text-yellow-300'
        : 'flex items-center space-x-1 bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1 rounded-full text-xs text-gray-300';
    }

    async function simulateDelivery() {
      await fetch('/api/inventory/deliver', { method: 'POST' });
      refreshAll();
    }

    async function injectDrift(type) {
      await fetch('/api/drift/inject?type=' + type, { method: 'POST' });
      refreshAll();
    }

    async function autoRepairDrift() {
      await fetch('/api/drift/repair', { method: 'POST' });
      refreshAll();
    }

    async function submitNewEncounter(e) {
      e.preventDefault();
      const payload = {
        triage_level: document.getElementById('form-triage').value,
        facility: document.getElementById('form-facility').value,
        condition: document.getElementById('form-condition').value,
        icd11: document.getElementById('form-icd11').value,
        snomed: document.getElementById('form-snomed').value,
        blood_panel: {
          blood_type: document.getElementById('form-blood-type').value,
          hb_g_dl: parseFloat(document.getElementById('form-hb').value),
          lactate_mmol_l: parseFloat(document.getElementById('form-lactate').value)
        },
        supplies: document.getElementById('form-supplies').value,
        notes: document.getElementById('form-notes').value,
        media: [
          { type: 'video', label: 'Thoracic Ultrasound Scan (Pneumothorax absence of lung sliding)', duration: '0:35', sha256: '9c8b7a...' },
          { type: 'audio', label: 'Medic Trauma Decompression Audio Log', duration: '0:42', sha256: '3f2e1d...' }
        ]
      };

      await fetch('/api/patients/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      closeNewEncounterModal();
      refreshAll();
    }

    async function refreshAll() {
      try {
        const [statusRes, balancesRes, transfersRes, invRes, patientsRes, driftRes] = await Promise.all([
          fetch('/api/status').then(r => r.json()),
          fetch('/api/balances').then(r => r.json()),
          fetch('/api/transfers').then(r => r.json()),
          fetch('/api/inventory').then(r => r.json()),
          fetch('/api/patients').then(r => r.json()),
          fetch('/api/drift/check').then(r => r.json())
        ]);

        // Update stats
        document.getElementById('header-offset').innerText = statusRes.metrics.last_synced_offset;
        document.getElementById('stream-offset').innerText = statusRes.metrics.last_synced_offset;
        document.getElementById('stat-contracts').innerText = statusRes.metrics.contracts_indexed;
        document.getElementById('stat-txs').innerText = statusRes.metrics.transactions_processed;
        
        const driftEl = document.getElementById('stat-drift');
        if (driftRes.drift_detected) {
          driftEl.innerText = `${driftRes.drift_count} Drift Detected!`;
          driftEl.className = 'text-2xl font-extrabold text-rose-400 mt-1';
        } else {
          driftEl.innerText = '0 Drift';
          driftEl.className = 'text-2xl font-extrabold text-emerald-400 mt-1';
        }

        // Inventory table
        document.getElementById('inventory-table').innerHTML = invRes.map(item => `
          <tr class="hover:bg-gray-800/40 transition">
            <td class="px-4 py-3 font-medium text-white">
              <div>${item.name}</div>
              <div class="text-[10px] text-gray-500 font-mono">${item.batch_id} (${item.item_id})</div>
            </td>
            <td class="px-4 py-3 text-teal-400">${item.category}</td>
            <td class="px-4 py-3 font-bold text-white">${item.quantity} ${item.unit}</td>
            <td class="px-4 py-3 text-gray-300"><i class="fa-solid fa-location-dot text-rose-400 mr-1"></i>${item.location}</td>
            <td class="px-4 py-3 font-mono text-[11px] text-gray-400">${item.custodian_party.slice(0, 22)}...</td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${item.temperature_c <= 8 ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-800' : 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'}">
                <i class="fa-solid fa-snowflake mr-1"></i>${item.cold_chain_status} (${item.temperature_c}°C)
              </span>
            </td>
          </tr>
        `).join('');

        // Patients EHR Cards
        document.getElementById('patients-cards').innerHTML = patientsRes.map(p => {
          let blood = {};
          let media = [];
          try { blood = JSON.parse(p.blood_panel || '{}'); } catch(e){}
          try { media = JSON.parse(p.media_attachments || '[]'); } catch(e){}

          return `
          <div class="glass rounded-xl p-5 border border-gray-800 space-y-3.5 hover:border-teal-500/40 transition">
            <!-- Header row -->
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-gray-800 pb-3">
              <div class="flex items-center space-x-3">
                <span class="px-2.5 py-1 rounded text-xs font-extrabold ${p.triage_level.includes('Red') ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-amber-950 text-amber-300 border border-amber-800'}">
                  ${p.triage_level}
                </span>
                <h3 class="text-sm font-bold text-white font-mono">${p.record_id}</h3>
                <span class="text-xs text-gray-400"><i class="fa-solid fa-hospital mr-1 text-teal-400"></i>${p.treating_facility}</span>
              </div>
              <div class="text-right">
                <span class="text-[11px] font-mono text-gray-500">Anon Hash: <strong class="text-gray-300">${p.patient_hash.slice(0, 16)}...</strong></span>
              </div>
            </div>

            <!-- Condition & Codes -->
            <div>
              <p class="text-sm font-medium text-gray-100">${p.condition_summary}</p>
              <div class="flex flex-wrap gap-2 mt-2">
                <span class="px-2 py-0.5 rounded bg-teal-950/80 text-teal-300 border border-teal-800 font-mono text-[11px]">
                  <i class="fa-solid fa-tag mr-1"></i>${p.icd11_code || 'WHO ICD-11'}
                </span>
                <span class="px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800 font-mono text-[11px]">
                  <i class="fa-solid fa-code-commit mr-1"></i>${p.snomed_concept || 'SNOMED-CT'}
                </span>
              </div>
            </div>

            <!-- Bloods Lab Panel & Supplies -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-900/60 p-3 rounded-lg border border-gray-800/80 text-xs">
              <div>
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1"><i class="fa-solid fa-droplet text-rose-400 mr-1"></i>Bloods & Point-of-Care Panel</p>
                <p class="text-gray-200">
                  <strong>Type:</strong> <span class="text-rose-300 font-bold">${blood.blood_type || 'O-Neg'}</span> | 
                  <strong>Hb:</strong> ${blood.hb_g_dl || '7.0'} g/dL | 
                  <strong>Lactate:</strong> ${blood.lactate_mmol_l || '3.5'} mmol/L
                </p>
              </div>
              <div>
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1"><i class="fa-solid fa-kit-medical text-amber-400 mr-1"></i>Allocated Supplies</p>
                <p class="text-amber-300 font-medium">${p.allocated_supplies}</p>
              </div>
            </div>

            <!-- Media Attachments & Audio Transcript -->
            <div class="space-y-2">
              <div class="flex flex-wrap gap-2">
                ${media.map(m => `
                  <span class="inline-flex items-center px-2 py-1 rounded bg-purple-950/60 text-purple-300 border border-purple-800 text-[11px] font-mono">
                    <i class="fa-solid ${m.type === 'video' ? 'fa-video' : (m.type === 'audio' ? 'fa-microphone' : 'fa-image')} mr-1.5 text-purple-400"></i>
                    ${m.label} ${m.duration ? '(' + m.duration + ')' : ''}
                  </span>
                `).join('')}
              </div>
              ${p.clinical_notes_transcript ? `
                <div class="bg-gray-900/40 p-2.5 rounded border border-gray-800/60 text-[11px] text-gray-300 font-sans italic">
                  <i class="fa-solid fa-quote-left text-gray-500 mr-1.5"></i>${p.clinical_notes_transcript}
                </div>
              ` : ''}
            </div>

            <!-- Escrow Tx & Cryptographic Audit Hash -->
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center text-[10px] text-gray-400 pt-1 font-mono border-t border-gray-800/60">
              <div><i class="fa-solid fa-link text-cyan-400 mr-1"></i>Canton Escrow: <span class="text-cyan-300">${p.escrow_tx_id}</span></div>
              <div><i class="fa-solid fa-stamp text-emerald-400 mr-1"></i>Audit Root: <span class="text-gray-400">${(p.audit_hash || '').slice(0, 24)}...</span></div>
            </div>
          </div>
          `;
        }).join('');

        // Balances list
        document.getElementById('balances-list').innerHTML = balancesRes.map(b => `
          <div class="bg-gray-900/60 p-3 rounded-lg border border-gray-800 flex justify-between items-center">
            <div>
              <p class="font-mono text-xs font-semibold text-white">${b.party}</p>
              <p class="text-[11px] text-gray-400">${b.utxo_count} UTXO contracts ${b.locked_count > 0 ? '(' + b.locked_count + ' locked)' : ''}</p>
            </div>
            <div class="text-right">
              <p class="text-sm font-bold text-teal-400">${b.total_balance.toLocaleString()} ${b.instrument}</p>
            </div>
          </div>
        `).join('');

        // Transfers list
        document.getElementById('transfers-list').innerHTML = transfersRes.map(tx => `
          <div class="bg-gray-900/40 p-2.5 rounded-lg border border-gray-800 text-xs flex justify-between items-center">
            <div class="space-y-0.5">
              <div class="flex items-center space-x-2 font-mono text-[11px]">
                <span class="text-cyan-400">${tx.sender.split('::')[0]}</span>
                <i class="fa-solid fa-arrow-right text-[9px] text-gray-500"></i>
                <span class="text-emerald-400">${tx.receiver.split('::')[0]}</span>
              </div>
              <div class="text-[10px] text-gray-500">${tx.timestamp} · Offset ${tx.offset}</div>
            </div>
            <span class="font-bold text-teal-300">+${tx.amount} ${tx.instrument}</span>
          </div>
        `).join('');

        // Nodes list
        document.getElementById('nodes-list').innerHTML = statusRes.nodes.map(n => `
          <div class="bg-gray-900/60 p-3 rounded-lg border border-gray-800 flex justify-between items-center">
            <div>
              <p class="font-bold text-xs text-white capitalize">${n.id.replace('_', ' ')}</p>
              <p class="text-[10px] text-gray-400 font-mono truncate max-w-[180px]">${n.url}</p>
            </div>
            <div class="text-right">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${n.status === 'online' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-gray-800 text-gray-400'}">
                ${n.status} (${n.latency_ms}ms)
              </span>
            </div>
          </div>
        `).join('');

        // Drift log
        document.getElementById('drift-log').innerHTML = statusRes.drift_logs.map(log => `
          <div class="p-2 rounded bg-gray-900/60 border border-gray-800 text-[11px] flex justify-between items-center">
            <div>
              <span class="font-mono font-bold ${log.resolution.includes('REPAIRED') ? 'text-emerald-400' : 'text-rose-400'}">${log.entity_type}</span>: 
              <span class="text-gray-300">${log.entity_id}</span>
              <div class="text-[10px] text-gray-500">${log.actual_state} &rarr; ${log.resolution} (${log.latency_ms}ms)</div>
            </div>
            <span class="text-[10px] text-gray-400">${log.detected_at.split(' ')[1] || ''}</span>
          </div>
        `).join('') || '<p class="text-gray-500 italic text-center py-2">No drift detected. System state is pristine.</p>';

      } catch (err) {
        console.error('Refresh error:', err);
      }
    }

    refreshAll();
    setInterval(refreshAll, 3000);
  </script>
</body>
</html>
"""

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet down logging for high frequency polls
        return

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path in ("/", "/index.html"):
            body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/status":
            self.send_json({
                "status": "online",
                "metrics": scanner.metrics,
                "nodes": scanner.nodes,
                "drift_logs": scanner.get_drift_logs(10)
            })
        elif path == "/api/balances":
            self.send_json(scanner.get_party_balances())
        elif path == "/api/transfers":
            self.send_json(scanner.get_recent_transfers())
        elif path == "/api/inventory":
            self.send_json(scanner.get_inventory())
        elif path == "/api/patients":
            self.send_json(scanner.get_patients())
        elif path == "/api/drift/check":
            self.send_json(sentinel.check_invariants())
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/drift/inject":
            attack_type = query.get("type", ["STUCK_SUBMISSION"])[0]
            res = sentinel.inject_drift_attack(attack_type)
            self.send_json(res)
        elif path == "/api/drift/repair":
            res = sentinel.auto_repair_drift()
            self.send_json(res)
        elif path == "/api/settings/low-data":
            scanner.low_data_mode = not scanner.low_data_mode
            self.send_json({"low_data_mode": scanner.low_data_mode})
        elif path == "/api/inventory/deliver":
            with scanner.get_db() as conn:
                conn.execute("UPDATE medical_inventory SET quantity = quantity + 25 WHERE item_id = 'MED-TRM-001'")
                conn.execute("""
                    INSERT INTO transfer_history (transaction_id, sender, receiver, instrument, amount, timestamp, offset, transfer_kind)
                    VALUES ('tx-dvp-escrow-deliver', 'Donor_ECHO::1220a1', 'Local_Transporter_01::1220t1', 'Amulet', 850.0, CURRENT_TIMESTAMP, '115', 'direct')
                """)
                conn.execute("UPDATE contracts SET amount = amount - 850.0 WHERE contract_id = 'c-amulet-donor-001'")
                conn.execute("UPDATE contracts SET amount = amount + 850.0 WHERE contract_id = 'c-amulet-courier-01'")
                conn.commit()
            scanner.set_last_offset("115")
            self.send_json({"status": "DELIVERY_AND_ESCROW_SETTLED_ATOMICALLY", "amount_paid": 850.0})
        elif path == "/api/patients/record":
            content_length = int(self.headers.get('Content-Length', 0))
            body_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            res = scanner.add_patient_encounter(
                triage_level=body_data.get('triage_level', 'Red (Immediate)'),
                condition=body_data.get('condition', 'Emergency Trauma Presentation'),
                icd11=body_data.get('icd11', 'ICD-11: ND33'),
                snomed=body_data.get('snomed', 'SNOMED-CT: 284530008'),
                blood_panel=body_data.get('blood_panel', {}),
                notes_transcript=body_data.get('notes', ''),
                media_meta=body_data.get('media', []),
                facility=body_data.get('facility', 'Field Hospital Alpha'),
                supplies=body_data.get('supplies', '1x Trauma Kit')
            )
            self.send_json(res)
        else:
            self.send_error(404, "Not Found")

def start_server(preferred_port=PORT):
    scanner.start_background_indexer()
    socketserver.TCPServer.allow_reuse_address = True
    
    ports_to_try = [preferred_port, 8088, 5050, 9090, 3050]
    server = None
    active_port = None
    
    for p in ports_to_try:
        try:
            server = socketserver.TCPServer(("", p), RequestHandler)
            active_port = p
            break
        except OSError:
            continue
            
    if not server:
        logger.error("Could not bind to any available port.")
        return

    logger.info(f"============================================================")
    logger.info(f"  IRONFLOWER SERVER RUNNING: http://localhost:{active_port}")
    logger.info(f"============================================================")
    print(f"\n>>> IronFlower Web Portal LIVE at: http://localhost:{active_port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        scanner.stop()
        server.server_close()

if __name__ == "__main__":
    start_server()
