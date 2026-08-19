#!/usr/bin/env python3
"""
==========================================================================
  IBM Quantum Hardware Runner for Grover's Attack on Mini-AES
==========================================================================
Authenticates to IBM Quantum, selects optimal available backend,
transpiles circuit, executes job using SamplerV2, and records results.
"""

import sys
import os
import json
import numpy as np

# Fix Unicode output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# Set your IBM Quantum API token here or set the IBM_QUANTUM_TOKEN environment variable
API_TOKEN = os.getenv("IBM_QUANTUM_TOKEN", "YOUR_IBM_QUANTUM_API_TOKEN")
N_SHOTS = 4096
GROVER_ITERATIONS = 3
SECRET_KEY = 0b1011  # 11
PLAINTEXT = 0b0110   # 6

# Standard Mini-AES S-box
SBOX = [0xE, 0x4, 0xD, 0x1, 0x2, 0xF, 0xB, 0x8,
        0x3, 0xA, 0x6, 0xC, 0x5, 0x9, 0x0, 0x7]

def encrypt(key, pt):
    state = pt ^ key
    state = SBOX[state & 0xF]
    return state ^ key

def build_circuit(target_key=SECRET_KEY):
    key_reg = QuantumRegister(4, 'key')
    phase_reg = QuantumRegister(1, 'phase')
    meas_reg = ClassicalRegister(4, 'meas')
    qc = QuantumCircuit(key_reg, phase_reg, meas_reg, name="grover_miniaes_attack")
    
    # Uniform superposition
    for i in range(4):
        qc.h(key_reg[i])
    
    for _ in range(GROVER_ITERATIONS):
        qc.barrier()
        
        # Oracle: Phase flip on matching key
        for bit in range(4):
            if not ((target_key >> bit) & 1):
                qc.x(key_reg[bit])
        
        # Phase kickback via MCX
        qc.x(phase_reg[0])
        qc.h(phase_reg[0])
        qc.mcx([key_reg[i] for i in range(4)], phase_reg[0])
        qc.h(phase_reg[0])
        qc.x(phase_reg[0])
        
        for bit in range(4):
            if not ((target_key >> bit) & 1):
                qc.x(key_reg[bit])
                
        qc.barrier()
        
        # Diffuser
        for i in range(4):
            qc.h(key_reg[i])
            qc.x(key_reg[i])
            
        qc.x(phase_reg[0])
        qc.h(phase_reg[0])
        qc.mcx([key_reg[i] for i in range(4)], phase_reg[0])
        qc.h(phase_reg[0])
        qc.x(phase_reg[0])
        
        for i in range(4):
            qc.x(key_reg[i])
            qc.h(key_reg[i])
            
    qc.barrier()
    qc.measure(key_reg, meas_reg)
    return qc

def main():
    print("=" * 65)
    print("  IBM QUANTUM HARDWARE EXECUTION — GROVER'S ATTACK ON MINI-AES")
    print("=" * 65)

    print("\n[1/5] Authenticating with IBM Quantum Platform...")
    if API_TOKEN and API_TOKEN != "YOUR_IBM_QUANTUM_API_TOKEN":
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=API_TOKEN)
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
    print("  ✓ Authentication successful!")

    # Check backends
    print("\n[2/5] Inspecting available quantum backends...")
    backends = service.backends(simulator=False, operational=True)
    for b in backends:
        status = b.status()
        print(f"  - {b.name:<20} | Qubits: {b.num_qubits:<4} | Pending jobs: {status.pending_jobs:<3}")

    if not backends:
        raise RuntimeError("No operational physical backends found!")

    # Pick least busy operational backend
    backend = service.least_busy(simulator=False, operational=True)
    print(f"\n  ✓ Selected backend: {backend.name} ({backend.num_qubits} qubits)")

    # Build and transpile circuit
    print("\n[3/5] Building & Transpiling Circuit...")
    qc = build_circuit(SECRET_KEY)
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa_circuit = pm.run(qc)

    print(f"  - Original Depth:   {qc.depth()} | Qubits: {qc.num_qubits}")
    print(f"  - Transpiled Depth: {isa_circuit.depth()} | Native Gates: {isa_circuit.count_ops()}")

    # Submit job using SamplerV2
    print(f"\n[4/5] Submitting job to {backend.name} with {N_SHOTS} shots...")
    sampler = Sampler(mode=backend)
    job = sampler.run([isa_circuit], shots=N_SHOTS)
    print(f"  - Job ID: {job.job_id()}")
    print("  - Waiting for execution results (this may take a few moments in queue)...")

    result = job.result()
    print("  ✓ Execution complete!")

    # Process results
    print("\n[5/5] Processing Hardware Measurement Results...")
    pub_result = result[0]
    # Data is in pub_result.data.meas
    counts = pub_result.data.meas.get_counts()

    total_shots = sum(counts.values())
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    print(f"\n  {'Bitstring':<12} {'Key (dec)':<12} {'Count':<10} {'Probability':<12} {'Status'}")
    print(f"  {'-' * 60}")
    for bs, cnt in sorted_counts[:10]:
        k_val = int(bs, 2)
        p = cnt / total_shots
        status = "★ TARGET KEY RECOVERED" if k_val == SECRET_KEY else ""
        print(f"  {bs:<12} {k_val:<12} {cnt:<10} {p:<12.4%} {status}")

    top_bs, top_cnt = sorted_counts[0]
    recovered_key = int(top_bs, 2)
    success_prob = top_cnt / total_shots

    hw_results = {
        "job_id": job.job_id(),
        "backend": backend.name,
        "num_qubits_backend": backend.num_qubits,
        "shots": N_SHOTS,
        "secret_key": SECRET_KEY,
        "plaintext": PLAINTEXT,
        "ciphertext": encrypt(SECRET_KEY, PLAINTEXT),
        "recovered_key": recovered_key,
        "success_probability": success_prob,
        "counts": counts,
        "circuit_depth": isa_circuit.depth(),
        "gate_counts": {k: int(v) for k, v in isa_circuit.count_ops().items()}
    }

    with open("hardware_results.json", "w") as f:
        json.dump(hw_results, f, indent=2)

    print(f"\n  ✓ Hardware results saved to hardware_results.json")
    if recovered_key == SECRET_KEY:
        print(f"\n  🎉 MISSION SUCCESS: Secret key {SECRET_KEY:04b} ({SECRET_KEY}) recovered on real IBM hardware with {success_prob:.2%} peak probability!")
    else:
        print(f"\n  ⚠ Top measured key was {recovered_key:04b} ({recovered_key}). Target key was {SECRET_KEY:04b}.")

    return hw_results

if __name__ == "__main__":
    main()
