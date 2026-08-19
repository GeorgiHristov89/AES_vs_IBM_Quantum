# Quantum Cryptanalysis: Grover's Attack on Mini-AES (IBM Quantum Hardware Benchmark)

An experimental quantum computing research project demonstrating **Grover's Algorithm** key search on a **Mini-AES block cipher** using **Qiskit 1.x** and the **IBM Quantum Platform** (`ibm_fez`, 156-qubit superconducting processor).

This repository contains clean, reproducible code to simulate the attack locally on classical hardware and execute it on real physical IBM Quantum Processing Units (QPUs).

---

## 📁 Repository Structure

```
.
├── README.md                   # Project documentation & run instructions
├── requirements.txt            # Python dependencies
├── mini_aes_grover.py          # Classical cipher + quantum oracle + Aer simulation
├── run_hardware.py             # 4-bit key Grover attack on IBM Quantum hardware
├── run_8bit_hardware.py        # 8-bit key Grover attack on IBM Quantum hardware
├── hardware_results.json       # Physical measurement distribution (4-bit run on ibm_fez)
├── hardware_8bit_results.json  # Physical measurement distribution (8-bit run on ibm_fez)
├── simulation_results.json     # Ideal 4-bit simulation data (Aer)
└── simulation_8bit_results.json# Ideal 8-bit simulation data (Aer)
```

---

## 🛠️ Prerequisites & Setup

### 1. Python Environment
Python 3.10+ is recommended.

```bash
# Clone or navigate to the repository
cd "path/to/AES"

# (Optional) Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure IBM Quantum API Token
To run on physical quantum hardware, you need an IBM Quantum account ([quantum.ibm.com](https://quantum.ibm.com)):

**Option A (Recommended — Save to local environment):**
```python
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform", 
    token="YOUR_IBM_QUANTUM_API_TOKEN", 
    overwrite=True
)
```

**Option B (Direct in script):**
Edit `API_TOKEN = "YOUR_TOKEN"` at the top of `run_hardware.py` and `run_8bit_hardware.py`.

---

## 🚀 Execution Instructions

### 1. Local Simulation (No IBM Quantum runtime required)
Validates the classical cipher, verifies the reversible quantum S-box synthesis, and executes a noise-free Grover search on `AerSimulator`:

```bash
python mini_aes_grover.py
```
- **Output:** Verifies round-trip encryption/decryption for all 256 pairs, constructs the Grover oracle, and recovers secret key `|1011⟩` with ~96.7% probability. Results are saved to `simulation_results.json`.

---

### 2. Run 4-Bit Attack on IBM Quantum Hardware
Submits the 4-bit key attack (16 key candidates, 3 Grover iterations) to the least-busy operational IBM Quantum processor:

```bash
python run_hardware.py
```
- **Execution Flow:**
  1. Authenticates to IBM Quantum Platform.
  2. Selects the optimal operational QPU (e.g., `ibm_fez` with 156 qubits).
  3. Transpiles to native basis gates (`cz`, `rz`, `sx`, `x`) at optimization level 3.
  4. Submits job via Qiskit Runtime `SamplerV2` for 4,096 shots.
  5. Outputs ranked bitstring distribution to console and saves to `hardware_results.json`.
- **Expected Outcome:** Secret key `|1011⟩` (decimal 11) emerges as the **#1 peak at ~15.2% probability**, well above the 6.25% random noise floor.

---

### 3. Run 8-Bit Attack on IBM Quantum Hardware (The Decoherence Limit)
Submits the 8-bit key attack (256 key candidates, 12 Grover iterations, 15 qubits with ancilla V-chain optimization):

```bash
python run_8bit_hardware.py
```
- **Execution Flow:**
  1. Submits 8,192 shots on physical hardware.
  2. Compiles to 2,051 physical CZ gates across depth 5,837.
  3. Outputs ranked measurement distribution and saves to `hardware_8bit_results.json`.
- **Expected Outcome:** Demonstrates the physical boundary of uncorrected NISQ hardware — cumulative gate error causes the signal to decay into flat thermal noise (~0.39%).

---

## 📊 Summary of Experimental Benchmarks

| Metric | 4-Bit Run (Physical Hardware) | 8-Bit Run (Physical Hardware) | Ideal Aer Simulator |
| :--- | :--- | :--- | :--- |
| **Search Space ($N$)** | 16 keys ($2^4$) | 256 keys ($2^8$) | 16 / 256 keys |
| **Grover Iterations** | 3 iterations | 12 iterations | 3 / 12 iterations |
| **Hardware Backend** | `ibm_fez` (156 Qubits) | `ibm_fez` (156 Qubits) | Classical CPU |
| **Transpiled Depth** | 1,086 | 5,837 | 32 |
| **Physical CZ Gates** | 368 CZ gates | 2,051 CZ gates | — |
| **Noise Floor** | 6.25% (1/16) | 0.39% (1/256) | 0.00% |
| **Target Key Peak** | **15.20% (Rank #1 — SUCCESS)** | **0.22% (Decayed to Noise)** | **96.66% / 99.98%** |
| **Hardware Status** | **KEY RECOVERED** | **DECOHERENCE LIMIT REACHED** | **IDEAL BASELINE** |

---

## 🛡️ Post-Quantum Cryptographic Implications (AES-128 vs AES-256)

1. **Grover's Quadratic Speedup $\mathcal{O}(\sqrt{N})$:**
   - Grover's algorithm does not exponentially break symmetric encryption the way Shor's algorithm breaks RSA/ECC. It only cuts the effective key length in half.
2. **AES-128:**
   - Security is reduced from 128-bit to 64-bit ($2^{64}$ operations). On a hypothetical 100 MHz fault-tolerant quantum computer, this requires ~5,850 years.
3. **AES-256:**
   - Security is reduced from 256-bit to 128-bit ($2^{128}$ operations). Even on a 100 MHz quantum computer, cracking AES-256 takes **$10^{23}\text{ years}$** (>7 Trillion times the age of the universe).
   - **Conclusion:** AES-256 is mathematically secure against quantum cryptanalysis forever.

---

## 📄 License & Attribution
Designed with **Qiskit 1.x** and **Qiskit Runtime**. Benchmarks derived from *Grassl et al. (PQCrypto)* and NIST Special Publication 800-175B.
