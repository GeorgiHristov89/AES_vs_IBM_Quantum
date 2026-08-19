#!/usr/bin/env python3
"""
==========================================================================
  IBM Quantum Hardware Runner: 8-bit Grover Attack on Mini-AES Key
==========================================================================
Submits the 8-bit key Grover attack (256 keys, 12 iterations, 15 qubits)
to the least-busy IBM Quantum processor via Qiskit Runtime SamplerV2.
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
SECRET_KEY_8BIT = 0b10101101  # = 173 (0xAD)
GROVER_ITERATIONS_8BIT = 12
N_SHOTS = 8192

def build_8bit_circuit(target_key=SECRET_KEY_8BIT, n_iterations=GROVER_ITERATIONS_8BIT):
    key_reg = QuantumRegister(8, 'key')
    phase_reg = QuantumRegister(1, 'phase')
    anc_reg = QuantumRegister(6, 'anc')
    meas_reg = ClassicalRegister(8, 'meas')
    
    qc = QuantumCircuit(key_reg, phase_reg, anc_reg, meas_reg, name="grover_8bit_hw")
    
    # 1. Superposition on 8 key qubits
    for i in range(8):
        qc.h(key_reg[i])
        
    for _ in range(n_iterations):
        qc.barrier()
        
        # ── Oracle: Phase flip target key ──
        for bit in range(8):
            if not ((target_key >> bit) & 1):
                qc.x(key_reg[bit])
                
        qc.x(phase_reg[0])
        qc.h(phase_reg[0])
        qc.mcx(key_reg, phase_reg[0], anc_reg, mode='v-chain')
        qc.h(phase_reg[0])
        qc.x(phase_reg[0])
        
        for bit in range(8):
            if not ((target_key >> bit) & 1):
                qc.x(key_reg[bit])
                
        qc.barrier()
        
        # ── Diffuser ──
        for i in range(8):
            qc.h(key_reg[i])
            qc.x(key_reg[i])
            
        qc.x(phase_reg[0])
        qc.h(phase_reg[0])
        qc.mcx(key_reg, phase_reg[0], anc_reg, mode='v-chain')
        qc.h(phase_reg[0])
        qc.x(phase_reg[0])
        
        for i in range(8):
            qc.x(key_reg[i])
            qc.h(key_reg[i])
            
    qc.barrier()
    qc.measure(key_reg, meas_reg)
    return qc

def main():
    print("=" * 70)
    print("  IBM QUANTUM HARDWARE EXECUTION — 8-BIT KEY GROVER ATTACK")
    print("=" * 70)

    print("\n[1/5] Authenticating with IBM Quantum Platform...")
    if API_TOKEN and API_TOKEN != "YOUR_IBM_QUANTUM_API_TOKEN":
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=API_TOKEN)
    else:
        service = QiskitRuntimeService(channel="ibm_quantum_platform")
    print("  ✓ Authentication successful!")

    # Inspect operational backends
    print("\n[2/5] Selecting least busy operational quantum backend...")
    backend = service.least_busy(simulator=False, operational=True)
    status = backend.status()
    print(f"  ✓ Target Backend: {backend.name} ({backend.num_qubits} Qubits, {status.pending_jobs} jobs in queue)")

    # Build and transpile circuit
    print(f"\n[3/5] Building & Transpiling 8-bit Grover Circuit (15 qubits, 12 iterations)...")
    qc = build_8bit_circuit(SECRET_KEY_8BIT, GROVER_ITERATIONS_8BIT)
    
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa_circuit = pm.run(qc)
    
    gate_ops = dict(isa_circuit.count_ops())
    print(f"  - Original Depth:   {qc.depth()} | Qubits: {qc.num_qubits}")
    print(f"  - Transpiled Depth: {isa_circuit.depth()} | Native Gates: {gate_ops}")

    # Submit job using SamplerV2
    print(f"\n[4/5] Submitting 8-bit attack job to {backend.name} for {N_SHOTS} shots...")
    sampler = Sampler(mode=backend)
    job = sampler.run([isa_circuit], shots=N_SHOTS)
    print(f"  - Job ID: {job.job_id()}")
    print("  - Running on physical superconducting processor...")

    result = job.result()
    print("  ✓ Execution complete!")

    # Process and rank results
    print("\n[5/5] Processing Hardware Measurement Distribution...")
    pub_result = result[0]
    counts = pub_result.data.meas.get_counts()

    total_shots = sum(counts.values())
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    print(f"\n  Top 10 Measurement Results out of 256 keys:")
    print(f"  {'Bitstring':<12} {'Key (dec)':<12} {'Count':<10} {'Probability':<12} {'Status'}")
    print("  " + "-" * 65)
    for bs, cnt in sorted_counts[:10]:
        k_val = int(bs, 2)
        p = cnt / total_shots
        status = "★ TARGET 8-BIT KEY" if k_val == SECRET_KEY_8BIT else ""
        print(f"  {bs:<12} {k_val:<12} {cnt:<10} {p:<12.2%} {status}")

    top_bs, top_cnt = sorted_counts[0]
    recovered_key = int(top_bs, 2)
    success_prob = top_cnt / total_shots

    # Check rank of target key
    target_rank = None
    target_prob = None
    for idx, (bs, cnt) in enumerate(sorted_counts):
        if int(bs, 2) == SECRET_KEY_8BIT:
            target_rank = idx + 1
            target_prob = cnt / total_shots
            break

    hw_results = {
        "job_id": job.job_id(),
        "backend": backend.name,
        "num_qubits_backend": backend.num_qubits,
        "shots": N_SHOTS,
        "n_bits": 8,
        "key_search_space": 256,
        "grover_iterations": GROVER_ITERATIONS_8BIT,
        "secret_key": SECRET_KEY_8BIT,
        "secret_key_bin": f"{SECRET_KEY_8BIT:08b}",
        "recovered_key": recovered_key,
        "target_rank": target_rank,
        "target_probability": target_prob,
        "counts": counts,
        "circuit_depth": isa_circuit.depth(),
        "gate_counts": {k: int(v) for k, v in gate_ops.items()}
    }

    with open("hardware_8bit_results.json", "w") as f:
        json.dump(hw_results, f, indent=2)

    print(f"\n  ✓ Hardware results saved to hardware_8bit_results.json")
    print(f"\n  Target Key {SECRET_KEY_8BIT:08b} (173): Rank #{target_rank} with probability {target_prob:.2%} (Noise floor: 0.39%)")

    return hw_results

if __name__ == "__main__":
    main()
