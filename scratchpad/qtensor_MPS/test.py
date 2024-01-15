import numpy as np
from gates import xgate, cnot, hgate, zgate, igate
from mps import MPS
from mpo import MPO, MPOLayer
import tensornetwork as tn
from constants import xmatrix, cnot_matrix


def test_from_wavefunction_all_zero_state():
    wavefunction = np.array([1, 0, 0, 0, 0, 0, 0, 0])
    mps = MPS.construct_mps_from_wavefunction(wavefunction, "q", 3, 2)

    assert mps.get_norm() == 1
    assert isinstance(mps, MPS)
    assert mps.N == 3
    assert mps.physical_dim == 2
    assert np.allclose(mps.get_wavefunction(), wavefunction)


def test_from_wavefunction_random():
    n = 3
    wavefunction = np.random.rand(2**n)
    wavefunction = wavefunction / np.linalg.norm(wavefunction, ord=2)
    mps = MPS.construct_mps_from_wavefunction(wavefunction, "q", n, 2)
    assert np.isclose(mps.get_norm(), 1.0)
    assert np.allclose(mps.get_wavefunction(), wavefunction)


def test_apply_one_qubit_mps_operation_xgate():
    # q0q1 = 00
    # On apply x gate |00> -> |10>
    mps = MPS("q", 2, 2)
    assert np.isclose(mps.get_norm(), 1.0)

    mps.apply_single_qubit_gate(xgate(), 0)
    mps.apply_single_qubit_gate(xgate(), 1)
    assert np.isclose(mps.get_norm(), 1.0)

    assert np.allclose(
        mps.get_wavefunction(), np.array([0.0, 0.0, 0.0, 1.0], dtype=np.complex64)
    )


def test_apply_twoq_cnot_two_qubits():
    # In the following tests, the first qubit is always the control qubit.
    # Check that CNOT|10> = |11>
    mps = MPS("q", 4, 2)
    assert np.isclose(mps.get_norm(), 1.0)

    # mps.apply_single_qubit_gate(xgate(), 0)
    mps.apply_two_qubit_gate(cnot(), [1, 2])
    # assert np.isclose(mps.get_norm(), 1.0)
    # assert np.allclose(
    #     mps.get_wavefunction(), np.array([0.0, 0.0, 0.0, 1.0], dtype=np.complex64)
    # )


def test_apply_two_twoq_cnot_two_qubits():
    # In the following tests, the first qubit is always the control qubit.
    # Check that CNOT(0,1)|100> = |110>
    # Check that CNOT(1,2)|110> = |111>
    mps = MPS("q", 3, 2)
    assert np.isclose(mps.get_norm(), 1.0)

    mps.apply_single_qubit_gate(xgate(), 0)
    mps.apply_two_qubit_gate(cnot(), [0, 1])
    mps.apply_two_qubit_gate(cnot(), [1, 2])
    assert np.isclose(mps.get_norm(), 1.0)
    assert np.allclose(
        mps.get_wavefunction(),
        np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.complex64),
    )


def test_apply_gate_for_bell_circuit():
    mps = MPS("q", 2, 2)
    assert np.isclose(mps.get_norm(), 1.0)

    mps.apply_single_qubit_gate(hgate(), 0)
    mps.apply_two_qubit_gate(cnot(), [0, 1])
    assert np.isclose(mps.get_norm(), 1.0)
    assert np.allclose(
        mps.get_wavefunction(),
        np.array([0.707106, 0.0, 0.0, 0.707106], dtype=np.complex64),
    )


def test_apply_gate_for_ghz_circuit():
    mps = MPS("q", 3, 2)
    assert np.isclose(mps.get_norm(), 1.0)

    mps.apply_single_qubit_gate(hgate(), 0)
    mps.apply_two_qubit_gate(cnot(), [0, 1])
    mps.apply_two_qubit_gate(cnot(), [1, 2])
    assert np.isclose(mps.get_norm(), 1.0)
    assert np.allclose(
        mps.get_wavefunction(),
        np.array([0.7071, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7071], dtype=np.complex64),
    )


def test_expectation_value_hgate():
    mps = MPS("q", 2, 2)
    copy = mps.__copy__()

    # <00|HI|00> = 1 / sqrt(2)
    np.isclose(mps.get_expectation(hgate(), 0), 1.0 / np.sqrt(2))
    assert mps.get_norm() == copy.get_norm()


def test_expectation_value_xgate():
    mps = MPS("q", 2, 2)
    copy = mps.__copy__()

    # <00|XI|00> = 0
    np.isclose(mps.get_expectation(xgate(), 0), 0.0)
    assert mps.get_norm() == copy.get_norm()


def test_expectation_value_xhgate():
    mps = MPS("q", 2, 2)
    copy = mps.__copy__()

    # <10|HI|10> = - 1 / sqrt(2)
    mps.apply_single_qubit_gate(xgate(), 0)
    np.isclose(mps.get_expectation(hgate(), 0), -1.0 / np.sqrt(2))
    assert mps.get_norm() == copy.get_norm()


def test_expectation_value_zgate():
    mps = MPS("q", 2, 2)
    copy = mps.__copy__()
    np.isclose(mps.get_expectation(zgate(), 0), 1.0)
    assert mps.get_norm() == copy.get_norm()


def test_expectation_value_xgate_at_k():
    k = 3
    n = 5
    mps = MPS("q", n, 2)
    copy = mps.__copy__()
    mps.apply_single_qubit_gate(xgate(), k)

    expectation_array = []

    for i in range(n):
        expectation_array.append(mps.get_expectation(zgate(), i))

    np.allclose(expectation_array, [1.0, 1.0, 1.0, -1.0, 1.0])


def test_mps_mpo():
    mps00 = MPS("q", 2, 2)
    mps01 = MPS("q", 2, 2)
    mps10 = MPS("q", 2, 2)
    mps11 = MPS("q", 2, 2)

    mps01.apply_mpo(MPO(xgate(), [1]))
    mps10.apply_mpo(MPO(xgate(), [0]))
    mps11.apply_mpo(MPO(xgate(), [0]))
    mps11.apply_mpo(MPO(xgate(), [1]))

    allmps = (mps00, mps01, mps10, mps11)

    # Test inner products
    for i in range(4):
        for j in range(4):
            assert np.isclose(allmps[i].inner_product(allmps[j]), i == j)


def test_mpo_two_qubit():
    mpo_layer = MPOLayer("q", 4, 2)
    # print("BEFORE")
    # print(mpo_layer._nodes)
    mpo_layer.add_two_qubit_gate(cnot(), [1, 2])
    print("AFTER")
    print(mpo_layer._nodes)
    # assert (mps1.get_wavefunction() == mps2.get_wavefunction()).all()


def test_mpo_single_qubit_gate():
    mps1 = MPS("q", 2, 2)
    mps1.apply_single_qubit_gate(xgate(), 0)
    print("MPS with gate", mps1.get_wavefunction())

    mpo = MPOLayer("q", 2, 2)
    mpo.add_single_qubit_gate(xgate(), 0)
    mps2 = MPS("q", 2, 2)
    mps2.apply_mpo_layer(mpo)
    print("MPS with MPO", mps2.get_wavefunction())

    condition = np.allclose(
        np.array(mps1.get_wavefunction()),
        np.array(mps2.get_wavefunction()),
        rtol=1e-05,
        atol=1e-08,
    )
    message = "Arrays are not equal within tolerance"

    assert condition, message


def test_mpo_two_qubit_gate():
    mps1 = MPS("q", 2, 2)
    mps1.apply_single_qubit_gate(xgate(), 1)
    mps1.apply_two_qubit_gate(cnot(), [0, 1])

    mpo = MPOLayer("q", 2, 2)
    mpo.add_single_qubit_gate(xgate(), 1)
    mpo.add_two_qubit_gate(cnot(), [0, 1])
    mps2 = MPS("q", 2, 2)

    mps2.apply_mpo_layer(mpo)

    condition = np.allclose(
        np.array(mps1.get_wavefunction()),
        np.array(mps2.get_wavefunction()),
        rtol=1e-05,
        atol=1e-08,
    )
    message = "MPO two qubit gate test failed"

    assert condition, message


def test_mpo_construction_from_pauli_string():
    pauli_string = "IXZXXXZZZZI"
    n = len(pauli_string)

    mpo = MPOLayer("q", n, 2)
    mpo.construct_mpo(pauli_string)

    mps1 = MPS("q", n, 2)
    for i, ps in enumerate(pauli_string):
        if ps == "X":
            mps1.apply_single_qubit_gate(xgate(), i)
        if ps == "Z":
            mps1.apply_single_qubit_gate(zgate(), i)

    mps2 = MPS("q", n, 2)
    mps2.apply_mpo_layer(mpo)

    condition = np.allclose(
        np.array(mps1.get_wavefunction()),
        np.array(mps2.get_wavefunction()),
        rtol=1e-05,
        atol=1e-08,
    )
    message = (
        "(gates) on MPS and (MPO pauli string on) MPS are not equal within tolerance"
    )

    assert condition, message


def test_mpo_mps_inner_prod():
    pauli_string = "IZI"
    n = len(pauli_string)
    mpo = MPOLayer("q", n, 2)
    mpo.construct_mpo(pauli_string)

    mps1 = MPS("q", n, 2)
    # mps1.apply_single_qubit_gate(xgate(), 1)

    inner_prod1 = mpo.mpo_mps_inner_prod(mps1)
    condition1 = np.allclose(
        inner_prod1,
        np.complex128(1),
        rtol=1e-05,
        atol=1e-08,
    )

    mps2 = MPS("q", n, 2)
    mps2.apply_single_qubit_gate(xgate(), 1)
    inner_prod2 = mpo.mpo_mps_inner_prod(mps2)

    condition2 = np.allclose(
        inner_prod2,
        np.complex128(-1),
        rtol=1e-05,
        atol=1e-08,
    )

    message = "MPO inner product gives error"

    assert condition1 and condition2, message


# test conjugate gate
def test_mpo_gate_conjugate():
    pauli_string = "IZI"
    n = len(pauli_string)
    mpo = MPOLayer("q", n, 2)
    mpo.construct_mpo(pauli_string)
    mpo.add_two_qubit_gate(cnot(), [0, 1])
    mpo.add_two_qubit_gate(cnot(), [0, 1], True)

    mps = MPS("q", 3, 2)

    print(mpo.mpo_mps_inner_prod(mps))
    # Add assert statement


# TODO:

# Initilisation given as pauli string and give mpo
# Test for CNOT - Pauli then apply cnot + decompose cnot
# expectation of an MPO - <psi| MPO | psi > psi = MPS (for this |psi | G1G2 X G2'G1' | psi>)

# write vector of mps kronector of IZI ||
test_mpo_gate_conjugate()
