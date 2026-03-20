"""
Comprehensive Chemistry Vectorstore
Covers all major NCERT Class 11 & 12 Chemistry chapters
"""

import json
from pathlib import Path
from datetime import datetime
import hashlib


def create_chunk_id(content: str, subject: str, index: int) -> str:
    """Create unique chunk ID."""
    hash_obj = hashlib.md5(content[:50].encode())
    return f"{subject}_{hash_obj.hexdigest()[:8]}_chunk_{index:04d}"


def create_comprehensive_chemistry_chunks():
    """Create comprehensive chemistry content covering ALL NCERT chapters."""
    
    topics = [
        # CLASS 11 - UNIT 1: BASIC CONCEPTS
        {
            "content": """Atomic Structure and Models: Atom is smallest particle of element retaining chemical properties. Dalton's Atomic Theory (1808): 
            Matter consists of indivisible atoms, atoms of same element are identical, chemical reactions involve rearrangement of atoms. Thomson's Model 
            (Plum pudding, 1898): Positive charge spread throughout sphere, electrons embedded like plums. Rutherford's Nuclear Model (1911): Gold foil 
            experiment, most atom is empty space, dense positive nucleus at center, electrons revolve around nucleus. Limitations: Couldn't explain stability 
            and line spectra. Bohr's Model (1913): Electrons revolve in fixed orbits (stationary states), energy absorbed/emitted when electron jumps between 
            orbits (E = hν), angular momentum quantized (mvr = nh/2π). Energy of nth orbit: En = -13.6/n² eV for hydrogen. Limitations: Works only for 
            hydrogen-like species, couldn't explain fine structure, Zeeman effect. Modern Quantum Mechanical Model: Wave-particle duality (de Broglie: λ = h/mv), 
            Heisenberg's Uncertainty Principle (Δx·Δp ≥ h/4π), Schrödinger wave equation, electrons in orbitals (probability regions), described by four quantum 
            numbers.""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 2", "topic": "Atomic Structure", "difficulty": "advanced"
        },
        {
            "content": """Quantum Numbers and Electronic Configuration: Four quantum numbers describe electron state: Principal quantum number (n): Energy level, 
            shell (K, L, M, N... for n=1,2,3,4...), values 1, 2, 3... Azimuthal quantum number (l): Subshell, orbital angular momentum, values 0 to n-1, 
            l=0 (s), l=1 (p), l=2 (d), l=3 (f). Magnetic quantum number (m or ml): Orientation of orbital, values -l to +l. Spin quantum number (s or ms): 
            Spin orientation, values +1/2 or -1/2. Orbital shapes: s (spherical), p (dumbbell, three orbitals px,py,pz), d (double dumbbell, five orbitals), 
            f (complex, seven orbitals). Electronic configuration: Distribution of electrons in orbitals. Aufbau principle: Electrons fill lowest energy 
            orbitals first. Order: 1s, 2s, 2p, 3s, 3p, 4s, 3d, 4p, 5s, 4d, 5p, 6s, 4f, 5d, 6p, 7s, 5f, 6d, 7p. Pauli Exclusion Principle: No two electrons 
            can have same four quantum numbers, maximum 2 electrons per orbital (opposite spins). Hund's Rule: Electrons occupy degenerate orbitals singly 
            with parallel spins before pairing. Examples: H (1s¹), He (1s²), C (1s² 2s² 2p²), N (1s² 2s² 2p³), O (1s² 2s² 2p⁴), Fe (1s² 2s² 2p⁶ 3s² 3p⁶ 4s² 3d⁶).""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 2", "topic": "Electronic Configuration", "difficulty": "advanced"
        },
        {
            "content": """Chemical Bonding - Ionic and Covalent: Chemical bond is force holding atoms together. Ionic bond (Electrovalent bond): Transfer of 
            electrons from metal to non-metal, electrostatic attraction between oppositely charged ions, e.g., NaCl (Na⁺Cl⁻). Properties: High melting/boiling 
            points, hard and brittle, conduct electricity in molten/aqueous state, soluble in polar solvents. Lattice energy: Energy released when gaseous ions 
            combine to form ionic crystal, higher for smaller ions and higher charges. Covalent bond: Sharing of electron pairs between atoms. Types: Single 
            bond (1 pair shared, e.g., H-H), Double bond (2 pairs, e.g., O=O), Triple bond (3 pairs, e.g., N≡N). Polar covalent: Unequal sharing, 
            electronegativity difference (e.g., H-Cl), dipole moment. Non-polar covalent: Equal sharing (e.g., H-H, Cl-Cl). Coordinate covalent (Dative bond): 
            Both electrons from same atom, e.g., NH3→BF3. Properties: Lower melting/boiling points than ionic, poor electrical conductors, soluble in non-polar 
            solvents. Lewis structures: Electron dot diagrams showing valence electrons, octet rule (8 electrons in valence shell for stability).""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 4", "topic": "Chemical Bonding", "difficulty": "intermediate"
        },
        {
            "content": """VSEPR Theory and Molecular Geometry: Valence Shell Electron Pair Repulsion (VSEPR) theory predicts molecular shape based on electron pair 
            repulsions. Electron pairs arrange to minimize repulsion. Repulsion order: Lone pair-Lone pair > Lone pair-Bond pair > Bond pair-Bond pair. 
            Molecular shapes: Linear (2 bond pairs, 180°, e.g., BeF2, CO2), Trigonal planar (3 bond pairs, 120°, e.g., BF3), Tetrahedral (4 bond pairs, 109.5°, 
            e.g., CH4), Trigonal bipyramidal (5 bond pairs, 90° and 120°, e.g., PCl5), Octahedral (6 bond pairs, 90°, e.g., SF6). With lone pairs: Bent/V-shaped 
            (2 bp + 2 lp, 104.5°, H2O; 2 bp + 1 lp, 119°, SO2), Trigonal pyramidal (3 bp + 1 lp, 107°, NH3), T-shaped (3 bp + 2 lp, e.g., ClF3), Square 
            pyramidal (5 bp + 1 lp, e.g., BrF5), Square planar (4 bp + 2 lp, e.g., XeF4). Hybridization: Mixing of atomic orbitals to form hybrid orbitals. 
            sp (linear, 2 orbitals, 180°), sp² (trigonal planar, 3 orbitals, 120°), sp³ (tetrahedral, 4 orbitals, 109.5°), sp³d (trigonal bipyramidal, 5 orbitals), 
            sp³d² (octahedral, 6 orbitals). Examples: C in CH4 (sp³), C in C2H4 (sp²), C in C2H2 (sp).""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 4", "topic": "Molecular Geometry and Hybridization", "difficulty": "advanced"
        },
        
        # CLASS 11 - THERMODYNAMICS
        {
            "content": """Thermodynamics - First Law: Thermodynamics studies energy changes in chemical/physical processes. System: Part of universe under study. 
            Surroundings: Rest of universe. Types: Open (exchange matter and energy), Closed (exchange energy only), Isolated (no exchange). State functions: 
            Depend only on state (P, V, T, U, H, S, G), path independent. Path functions: Depend on path (heat q, work w), path dependent. Internal energy (U): 
            Total energy of system. First Law: Energy conserved, ΔU = q + w. Convention: Heat absorbed by system (+), heat released (-), work done by system (-), 
            work done on system (+). Work: w = -PΔV for expansion against constant external pressure. Enthalpy (H): H = U + PV, heat content at constant pressure. 
            ΔH = qp (heat at constant pressure). Exothermic: ΔH negative, heat released (e.g., combustion). Endothermic: ΔH positive, heat absorbed (e.g., 
            evaporation). Standard enthalpy change (ΔH°): At 298K, 1 bar pressure. Types: Enthalpy of formation (ΔfH°), combustion (ΔcH°), neutralization, 
            solution, atomization, bond enthalpy. Hess's Law: Total enthalpy change is same regardless of path, allows calculation of unknown ΔH.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 6", "topic": "First Law of Thermodynamics", "difficulty": "advanced"
        },
        {
            "content": """Thermodynamics - Entropy and Free Energy: Entropy (S): Measure of disorder/randomness. Second Law: In spontaneous process, total entropy 
            increases (ΔStotal = ΔSsystem + ΔSsurroundings > 0). ΔS positive for: Solid→Liquid→Gas, Dissolution, Increase in temperature, Increase in number of 
            particles. Third Law: Entropy of perfect crystal at 0 K is zero. Gibbs Free Energy (G): G = H - TS. Spontaneity criterion at constant T and P: 
            ΔG < 0 (spontaneous, feasible), ΔG = 0 (equilibrium), ΔG > 0 (non-spontaneous). ΔG = ΔH - TΔS. Process spontaneous if: ΔH negative and ΔS positive 
            (always spontaneous), ΔH negative and ΔS negative (low temperature), ΔH positive and ΔS positive (high temperature), ΔH positive and ΔS negative 
            (never spontaneous). Standard Gibbs energy change: ΔG° = -RT ln K (K is equilibrium constant). If K > 1, ΔG° negative (product favored). 
            If K < 1, ΔG° positive (reactant favored).""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 6", "topic": "Entropy and Gibbs Energy", "difficulty": "advanced"
        },
        
        # CLASS 11 - EQUILIBRIUM
        {
            "content": """Chemical Equilibrium: Reversible reaction reaches equilibrium when forward and reverse reaction rates equal. Equilibrium constant (Kc): 
            For aA + bB ⇌ cC + dD, Kc = [C]^c[D]^d / [A]^a[B]^b. Kp for gases: Kp = (PC)^c(PD)^d / (PA)^a(PB)^b. Relation: Kp = Kc(RT)^Δn, where Δn = (moles of 
            gaseous products) - (moles of gaseous reactants). Units: Depend on Δn. If Δn = 0, Kp = Kc. Large K: Products favored, equilibrium shifts right. 
            Small K: Reactants favored, equilibrium shifts left. K = 1: Equal amounts. Le Chatelier's Principle: If stress applied to equilibrium, system adjusts 
            to counteract stress. Concentration change: Increasing reactants or removing products shifts right. Pressure change: Increasing pressure shifts toward 
            fewer moles of gas. Temperature change: Increasing temperature favors endothermic direction. Catalyst: Increases rate, doesn't affect equilibrium 
            position or K value. Ionic Equilibrium: Weak acids/bases partially ionize. Ostwald's dilution law: Ka = α²C/(1-α) for weak acids. pH = -log[H⁺], 
            pOH = -log[OH⁻], pH + pOH = 14. Buffer solutions: Resist pH change, e.g., CH3COOH + CH3COONa (acidic buffer), NH4OH + NH4Cl (basic buffer). 
            Henderson-Hasselbalch equation: pH = pKa + log([Salt]/[Acid]).""",
            "class": "Class 11", "unit": "Unit 3", "chapter": "Chapter 7", "topic": "Chemical Equilibrium", "difficulty": "advanced"
        },
        
        # CLASS 11 - REDOX REACTIONS
        {
            "content": """Redox Reactions: Oxidation-reduction (redox) involves electron transfer. Oxidation: Loss of electrons, increase in oxidation number. 
            Reduction: Gain of electrons, decrease in oxidation number. Reducing agent (reductant): Loses electrons, gets oxidized. Oxidizing agent (oxidant): 
            Gains electrons, gets reduced. Oxidation number rules: Free element = 0, monatomic ion = charge, H = +1 (except in hydrides -1), O = -2 (except in 
            peroxides -1, OF2 +2), alkali metals = +1, alkaline earth metals = +2, halogens = -1 in binary compounds, sum = charge on species. Example: 
            Zn + Cu²⁺ → Zn²⁺ + Cu (Zn oxidized 0→+2, Cu²⁺ reduced +2→0). Balancing redox equations: Half-reaction method (separate oxidation and reduction, 
            balance atoms and charges, combine) or Oxidation number method. Disproportionation: Same element both oxidized and reduced, e.g., Cl2 + 2OH⁻ → 
            Cl⁻ + ClO⁻ + H2O (Cl: 0 → -1 and +1). Electrochemical cells: Galvanic/Voltaic (spontaneous, ΔG<0, produces electricity), Electrolytic (non-spontaneous, 
            ΔG>0, consumes electricity). Standard electrode potential (E°): Tendency to gain electrons. Higher E° = better oxidizing agent. EMF of cell: 
            E°cell = E°cathode - E°anode. If E°cell > 0, reaction spontaneous.""",
            "class": "Class 11", "unit": "Unit 3", "chapter": "Chapter 8", "topic": "Redox Reactions", "difficulty": "advanced"
        },
        
        # CLASS 11 - ORGANIC CHEMISTRY BASICS
        {
            "content": """Organic Chemistry - Basics and IUPAC Nomenclature: Organic compounds contain carbon. Carbon unique: Tetravalent, catenation (self-linking), 
            multiple bonding. Structural representations: Structural formula, condensed formula, bond-line formula. Homologous series: Series with same functional 
            group, differ by CH2, similar chemical properties. Functional groups: -OH (alcohol), -CHO (aldehyde), >C=O (ketone), -COOH (carboxylic acid), -NH2 (amine), 
            -X (halogen), -OR (ether), -COO- (ester). IUPAC Nomenclature: Select longest carbon chain (parent chain). Number from end nearest substituent. 
            Name substituents with position numbers (alphabetical order). Multiple substituents: di, tri, tetra. Examples: CH3CH2CH3 (propane), CH3CH(CH3)CH3 
            (2-methylpropane), CH3CH2OH (ethanol), CH3CHO (ethanal), CH3COCH3 (propan-2-one), CH3COOH (ethanoic acid). Isomerism: Same molecular formula, different 
            structures. Structural isomers: Different connectivity (chain, position, functional). Stereoisomers: Same connectivity, different spatial arrangement 
            (geometrical, optical). Geometrical (cis-trans): Different groups on C=C. Optical: Non-superimposable mirror images, chiral carbon (asymmetric, 
            4 different groups), rotate plane-polarized light.""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 12", "topic": "Organic Chemistry Basics", "difficulty": "intermediate"
        },
        {
            "content": """Hydrocarbons - Alkanes, Alkenes, Alkynes: Hydrocarbons contain only C and H. Alkanes (CnH2n+2): Saturated (single bonds), sp³ hybridized, 
            tetrahedral. General formula CnH2n+2. Nomenclature: -ane suffix. Preparation: Wurtz reaction (R-X + Na), Kolbe's electrolysis, decarboxylation. 
            Properties: Non-polar, insoluble in water, soluble in organic solvents, low reactivity. Reactions: Halogenation (free radical substitution, sunlight), 
            Combustion (produces CO2 and H2O). Conformations: Staggered (more stable) and eclipsed in ethane. Alkenes (CnH2n): Unsaturated (C=C), sp² hybridized, 
            trigonal planar. Nomenclature: -ene suffix, number indicates position of double bond. Preparation: Dehydration of alcohols (H2SO4, heat), 
            Dehydrohalogenation (KOH, alcohol). Reactions: Addition reactions (H2, HX, H2O, X2), Markovnikov's rule (H adds to C with more H in HX addition), 
            Anti-Markovnikov (peroxide effect for HBr), Ozonolysis, Polymerization. Alkynes (CnH2n-2): Unsaturated (C≡C), sp hybridized, linear. Nomenclature: 
            -yne suffix. Preparation: Dehalogenation. Reactions: Addition (H2, HX, H2O), acidic H in terminal alkynes. Benzene (C6H6): Aromatic, resonance 
            stabilized, undergoes electrophilic substitution (nitration, halogenation, sulphonation, Friedel-Crafts alkylation/acylation).""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 13", "topic": "Hydrocarbons", "difficulty": "advanced"
        },
        
        # CLASS 12 - SOLID STATE
        {
            "content": """Solid State: Solids have definite shape and volume. Classification: Crystalline (ordered arrangement, sharp melting point, anisotropic, 
            e.g., NaCl, quartz) and Amorphous (random arrangement, no sharp melting point, isotropic, e.g., glass, rubber). Crystal lattice: 3D arrangement of 
            points. Unit cell: Smallest repeating unit. Seven crystal systems: Cubic, tetragonal, orthorhombic, monoclinic, triclinic, hexagonal, rhombohedral. 
            14 Bravais lattices. Cubic unit cells: Simple cubic (SCC, 1 atom per unit cell, CN=6, packing efficiency 52%), Body-centered cubic (BCC, 2 atoms, 
            CN=8, 68%), Face-centered cubic (FCC, 4 atoms, CN=12, 74%). Close packing: hcp and ccp (both 74% efficiency, CN=12). Coordination number: Number of 
            nearest neighbors. Packing efficiency = (Volume occupied by atoms / Total volume) × 100. Voids: Tetrahedral (smaller, 2:1 ratio to atoms), Octahedral 
            (larger, 1:1 ratio). Ionic solids: Cations in voids of anion lattice. NaCl (rock salt) structure: FCC of Cl⁻, Na⁺ in octahedral voids. ZnS (zinc 
            blende) structure: FCC of S²⁻, Zn²⁺ in alternate tetrahedral voids. CaF2 (fluorite) structure: FCC of Ca²⁺, F⁻ in all tetrahedral voids.""",
            "class": "Class 12", "unit": "Unit 1", "chapter": "Chapter 1", "topic": "Solid State", "difficulty": "advanced"
        },
        
        # CLASS 12 - ELECTROCHEMISTRY
        {
            "content": """Electrochemistry - Galvanic Cells: Study of interconversion of chemical and electrical energy. Galvanic/Voltaic cell: Converts chemical 
            to electrical energy. Daniel cell: Zn|ZnSO4||CuSO4|Cu. Anode (oxidation): Zn → Zn²⁺ + 2e⁻. Cathode (reduction): Cu²⁺ + 2e⁻ → Cu. Salt bridge: 
            Maintains electrical neutrality, completes circuit. EMF (Electromotive force): E°cell = E°cathode - E°anode. Standard electrode potential: Measured 
            vs Standard Hydrogen Electrode (SHE, E° = 0V). Higher E° = stronger oxidizing agent. Nernst equation: E = E° - (RT/nF)ln Q = E° - (0.0591/n)log Q 
            at 298K. At equilibrium, E = 0, ΔG = 0. Relation: ΔG° = -nFE°cell. Conductance: Reciprocal of resistance, G = 1/R. Unit: Siemens (S) or mho. 
            Specific conductance (κ): Conductance of 1cm³ solution. Molar conductivity (Λm): Conductance of solution containing 1 mole electrolyte. 
            Λm = κ × 1000/M. Kohlrausch's law: Λ°m = λ°+ + λ°- (molar conductivity at infinite dilution). Applications: Calculate degree of dissociation, 
            solubility of sparingly soluble salts.""",
            "class": "Class 12", "unit": "Unit 2", "chapter": "Chapter 3", "topic": "Electrochemistry", "difficulty": "advanced"
        },
        {
            "content": """Electrochemistry - Electrolytic Cells and Batteries: Electrolytic cell: Converts electrical to chemical energy (non-spontaneous). 
            Electrolysis: Decomposition by electricity. Anode (+ve): Oxidation. Cathode (-ve): Reduction. Aqueous solution: Preferential discharge at anode 
            (most easily oxidized), at cathode (most easily reduced). Faraday's laws: First law: Mass deposited ∝ charge passed (m ∝ Q). Second law: Masses 
            of different substances deposited by same charge ∝ equivalent weights. m = ZIt = (E/F)It, where Z = electrochemical equivalent, F = 96500 C/mol. 
            Batteries: Primary cells (irreversible, e.g., dry cell, mercury cell), Secondary cells (rechargeable, e.g., lead-acid battery Pb + PbO2 + H2SO4, 
            Ni-Cd battery), Fuel cells (continuous supply, e.g., H2-O2 fuel cell produces H2O). Corrosion: Deterioration of metals by electrochemical process. 
            Rust (Fe): Anode Fe → Fe²⁺ + 2e⁻, Cathode O2 + 4H⁺ + 4e⁻ → 2H2O, Fe²⁺ oxidized to Fe2O3·xH2O (rust). Prevention: Painting, galvanization (Zn coating), 
            alloying, sacrificial anode (more reactive metal).""",
            "class": "Class 12", "unit": "Unit 2", "chapter": "Chapter 3", "topic": "Electrolysis and Batteries", "difficulty": "advanced"
        },
        
        # CLASS 12 - CHEMICAL KINETICS
        {
            "content": """Chemical Kinetics: Study of reaction rates and mechanisms. Rate of reaction: Change in concentration per unit time. Rate = -d[R]/dt = d[P]/dt. 
            Average rate vs instantaneous rate. Factors affecting rate: Concentration, temperature, catalyst, surface area, nature of reactants. Rate law: 
            Rate = k[A]^m[B]^n, where k = rate constant, m, n = order of reaction (determined experimentally, not from stoichiometry). Overall order = m + n. 
            Zero order: Rate = k (independent of concentration, e.g., photochemical reactions), t1/2 = [A]0/2k. First order: Rate = k[A], t1/2 = 0.693/k 
            (independent of initial concentration, e.g., radioactive decay), integrated rate equation: ln[A] = ln[A]0 - kt. Second order: Rate = k[A]², 
            t1/2 = 1/k[A]0. Molecularity: Number of species taking part in elementary step, always whole number (1 unimolecular, 2 bimolecular, 3 termolecular). 
            Temperature dependence: Arrhenius equation k = Ae^(-Ea/RT), where Ea = activation energy (minimum energy for reaction), A = frequency factor. 
            ln k = ln A - Ea/RT. Catalyst: Increases rate by providing alternate pathway with lower Ea, doesn't affect thermodynamics (ΔG, equilibrium). 
            Collision theory: Molecules must collide with sufficient energy (≥Ea) and proper orientation.""",
            "class": "Class 12", "unit": "Unit 3", "chapter": "Chapter 4", "topic": "Chemical Kinetics", "difficulty": "advanced"
        },
        
        # CLASS 12 - ALCOHOLS, PHENOLS, ETHERS
        {
            "content": """Alcohols, Phenols, Ethers: Alcohols (R-OH): Classification by carbon bearing OH: Primary (1°), Secondary (2°), Tertiary (3°). 
            Nomenclature: -ol suffix. Preparation: Hydration of alkenes, reduction of carbonyl compounds (LiAlH4 or NaBH4), Grignard reagent. Properties: 
            Polar, H-bonding (higher BP than corresponding alkanes), soluble in water (small alcohols). Reactions: Oxidation (1° → aldehyde → acid, 2° → ketone, 
            3° resistant), Dehydration (H2SO4, 443K → alkene, 413K → ether), Esterification (with carboxylic acid/acyl chloride), Reaction with Na (liberates H2), 
            HX (Lucas test). Phenols (Ar-OH): OH directly attached to benzene ring. Nomenclature: -ol or phenol suffix. Preparation: Dow process, cumene process. 
            Properties: Weakly acidic (more acidic than alcohols due to resonance stabilization of phenoxide ion), soluble in alkali. Reactions: Electrophilic 
            substitution (highly activated benzene ring, ortho/para directing, e.g., nitration, halogenation), Reimer-Tiemann reaction (CHCl3 + NaOH → salicylaldehyde), 
            Kolbe's reaction (CO2, high P → salicylic acid). Ethers (R-O-R'): Nomenclature: alkoxy alkane or common names. Preparation: Williamson synthesis 
            (R-O-Na + R'-X), Dehydration of alcohols. Properties: Polar but no H-bonding between ether molecules, low BP, good solvents. Reactions: Cleavage by HI.""",
            "class": "Class 12", "unit": "Unit 5", "chapter": "Chapter 11", "topic": "Alcohols, Phenols, Ethers", "difficulty": "advanced"
        },
        {
            "content": """Aldehydes and Ketones: Carbonyl compounds (>C=O). Aldehydes (R-CHO): Carbonyl at end of chain. Ketones (R-CO-R'): Carbonyl in middle. 
            Nomenclature: Aldehydes -al, Ketones -one. Preparation: Oxidation of alcohols (aldehydes from 1°, ketones from 2°), Ozonolysis of alkenes, 
            Friedel-Crafts acylation (ketones). Properties: Polar, H-bonding with water (lower aldehydes soluble), higher BP than hydrocarbons. Reactions: 
            Nucleophilic addition (due to partial positive on C=O). HCN → cyanohydrin, NaHSO3 → bisulfite addition product, Grignard reagent → alcohol. 
            Reduction: LiAlH4 or NaBH4 → alcohols (1° from aldehydes, 2° from ketones). Oxidation: Aldehydes easily oxidized (Tollen's test - silver mirror, 
            Fehling's test - red ppt), ketones resist oxidation. Aldol condensation: Aldehydes/ketones with α-H undergo self-condensation in presence of dilute 
            alkali → β-hydroxy aldehyde/ketone. Cannizzaro reaction: Aldehydes without α-H undergo disproportionation in concentrated alkali → alcohol + carboxylic 
            acid salt. Iodoform test: Methyl ketones/aldehydes/secondary alcohols with CH3-CO/CH3-CHOH group give yellow ppt of CHI3 with I2 + NaOH. 
            Distinguish aldehydes from ketones: Tollen's, Fehling's test.""",
            "class": "Class 12", "unit": "Unit 5", "chapter": "Chapter 12", "topic": "Aldehydes and Ketones", "difficulty": "advanced"
        },
        {
            "content": """Carboxylic Acids and Derivatives: Carboxylic acids (R-COOH): Functional group -COOH. Nomenclature: -oic acid suffix or common names 
            (formic, acetic, benzoic). Preparation: Oxidation of primary alcohols/aldehydes, Grignard reagent + CO2, hydrolysis of nitriles/esters/amides. 
            Properties: More acidic than phenols (resonance in carboxylate ion), dimerization due to H-bonding, soluble in water (lower acids). Reactions: 
            Acidic (donate H⁺, neutralization, salt formation), Hell-Volhard-Zelinsky reaction (α-halogenation using Cl2/Br2 + red P), Reduction (LiAlH4 → 
            primary alcohol), Decarboxylation (soda lime → alkane). Acidity order: Cl-CH2-COOH > HCOOH > CH3COOH (electron-withdrawing groups increase acidity). 
            Acid derivatives: Acyl halides (R-COCl, most reactive), Acid anhydrides ((RCO)2O), Esters (R-COOR'), Amides (R-CONH2, least reactive). 
            Preparation: From carboxylic acids. Reactions: Nucleophilic acyl substitution. Esterification: Acid + alcohol ⇌ ester + water (H⁺ catalyst). 
            Saponification: Ester + NaOH → soap (sodium salt of fatty acid) + glycerol. Ammonolysis: Ester/acyl chloride + NH3 → amide.""",
            "class": "Class 12", "unit": "Unit 5", "chapter": "Chapter 12", "topic": "Carboxylic Acids", "difficulty": "advanced"
        },
        
        # CLASS 12 - AMINES
        {
            "content": """Amines: Organic derivatives of ammonia (NH3). Classification: Primary (R-NH2), Secondary (R2NH), Tertiary (R3N). Nomenclature: 
            alkanamine or common names (methylamine, aniline). Preparation: Reduction of nitro compounds, nitriles, amides. Gabriel phthalimide synthesis 
            (primary amines), Hoffmann bromamide degradation. Properties: Basic (due to lone pair on N), basicity order: Aliphatic amines > ammonia > aromatic 
            amines (in gas phase: 2° > 1° > 3°, in aqueous solution: 2° > 1° > 3° due to steric and solvation factors). Aniline less basic (lone pair delocalized 
            into benzene ring). Reactions: Alkylation, Acylation (reaction with acyl chloride/anhydride → amide), Carbylamine reaction (1° amines + CHCl3 + KOH 
            → foul-smelling isocyanide, test for 1° amines), Diazotization (aniline + NaNO2 + HCl, 273-278K → benzene diazonium chloride), Coupling reaction 
            (diazonium salt + phenol/aromatic amine → azo dye). Hoffmann mustard oil reaction (1° amine + CS2 + HgCl2 → isothiocyanate). Distinguish: 
            1°/2°/3° amines using Hinsberg reagent (benzenesulphonyl chloride + KOH - 1° soluble in alkali, 2° insoluble, 3° no reaction).""",
            "class": "Class 12", "unit": "Unit 5", "chapter": "Chapter 13", "topic": "Amines", "difficulty": "advanced"
        },
        
        # CLASS 12 - BIOMOLECULES
        {
            "content": """Biomolecules - Carbohydrates: Carbohydrates (polyhydroxy aldehydes/ketones or derivatives). General formula (CH2O)n. Classification: 
            Monosaccharides (simplest, cannot be hydrolyzed, e.g., glucose, fructose), Oligosaccharides (2-10 units, e.g., disaccharides - sucrose, maltose, 
            lactose), Polysaccharides (many units, e.g., starch, cellulose, glycogen). Glucose (C6H12O6): Aldohexose, exists as pyranose ring (6-membered), 
            α-D-glucose (OH on C1 down) and β-D-glucose (OH on C1 up) anomers. Reactions: Reduction (sorbitol), Oxidation (gluconic acid, saccharic acid), 
            Glycoside formation, Acetylation. Fructose: Ketohexose, furanose ring (5-membered), sweetest sugar. Disaccharides: Sucrose (glucose + fructose, 
            α-glycosidic linkage, non-reducing), Maltose (glucose + glucose, reducing), Lactose (glucose + galactose, reducing). Reducing sugars: Free aldehyde/ketone 
            group (give positive Fehling's, Benedict's test). Polysaccharides: Starch (α-1,4 and α-1,6 glycosidic linkage, amylose + amylopectin, storage in 
            plants), Cellulose (β-1,4 glycosidic linkage, structural in plants, most abundant), Glycogen (storage in animals).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 14", "topic": "Carbohydrates", "difficulty": "intermediate"
        },
        {
            "content": """Biomolecules - Proteins and Enzymes: Proteins: Polymers of amino acids. Amino acids: Contain -NH2 and -COOH groups. General structure 
            R-CH(NH2)-COOH. 20 standard amino acids. Essential amino acids (cannot be synthesized by body, must be obtained from diet). Zwitterion: Dipolar ion 
            at isoelectric point. Peptide bond: -CO-NH- linkage between amino acids (condensation reaction). Structure: Primary (sequence of amino acids), 
            Secondary (α-helix, β-pleated sheet, H-bonding), Tertiary (3D folding, disulfide bonds, ionic interactions, H-bonds, hydrophobic interactions), 
            Quaternary (multiple polypeptide chains, e.g., hemoglobin has 4 subunits). Denaturation: Loss of structure and function due to heat, pH change, 
            chemicals. Enzymes: Biological catalysts (proteins). Highly specific, work under mild conditions. Active site: Region where substrate binds. 
            Lock-and-key model: Enzyme and substrate have complementary shapes. Factors affecting: Temperature (optimum ~37°C), pH (optimum varies), 
            substrate concentration. Cofactors: Non-protein helper molecules (metal ions). Coenzymes: Organic cofactors (vitamins). Inhibitors: Competitive 
            (bind to active site), Non-competitive (bind elsewhere, change shape).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 14", "topic": "Proteins and Enzymes", "difficulty": "advanced"
        },
        {
            "content": """Biomolecules - Nucleic Acids: Nucleic acids store and transmit genetic information. DNA (Deoxyribonucleic Acid) and RNA (Ribonucleic Acid). 
            Composed of nucleotides. Nucleotide = Nitrogenous base + Pentose sugar + Phosphate. Nitrogenous bases: Purines (Adenine-A, Guanine-G), Pyrimidines 
            (Cytosine-C, Thymine-T in DNA, Uracil-U in RNA). Sugar: Deoxyribose (in DNA), Ribose (in RNA, extra OH at C2'). DNA structure: Double helix (Watson-Crick), 
            two antiparallel strands, sugar-phosphate backbone, bases inside, complementary base pairing A-T (2 H-bonds), G-C (3 H-bonds), diameter 20Å, pitch 34Å, 
            10 bp per turn. Chargaff's rules: A=T, G=C. Functions of DNA: Storage of genetic information, replication, transcription. RNA: Single stranded (can 
            fold into secondary structures), contains ribose and uracil. Types: mRNA (messenger, carries genetic code from DNA to ribosome, 5% of total), 
            tRNA (transfer, brings amino acids to ribosome, cloverleaf structure, anticodon, 15%), rRNA (ribosomal, component of ribosomes, 80%). Differences 
            DNA vs RNA: Sugar (deoxyribose vs ribose), Bases (T vs U), Structure (double vs single strand), Stability (more vs less stable), Location (nucleus vs 
            nucleus and cytoplasm).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 14", "topic": "Nucleic Acids", "difficulty": "advanced"
        },
        
        # CLASS 12 - POLYMERS
        {
            "content": """Polymers: Large molecules made of repeating units (monomers). Classification by source: Natural (starch, cellulose, proteins, rubber), 
            Synthetic (polythene, nylon, PVC), Semi-synthetic (cellulose acetate, vulcanized rubber). Classification by structure: Linear (monomers in straight 
            chain, e.g., PVC, polythene), Branched (side chains, e.g., low-density polythene), Cross-linked (3D network, e.g., bakelite, vulcanized rubber). 
            Classification by mode of polymerization: Addition polymers (monomers add without loss of molecule, e.g., polythene from ethene, PVC from vinyl chloride, 
            polystyrene, teflon). Condensation polymers (monomers condense with loss of small molecule like H2O, e.g., nylon-6,6 from hexamethylene diamine + 
            adipic acid, terylene/dacron from ethylene glycol + terephthalic acid, bakelite from phenol + formaldehyde). Classification by molecular forces: 
            Elastomers (weak intermolecular forces, elastic, e.g., rubber), Fibers (strong intermolecular forces, H-bonds, high tensile strength, e.g., nylon, 
            polyester), Thermoplastics (intermediate forces, can be molded on heating, e.g., polythene, PVC), Thermosetting (cross-linked, cannot be remelted, 
            e.g., bakelite). Biodegradable polymers: PHBV, nylon-2-nylon-6. Important polymers: Polythene (HDPE, LDPE), PVC, Teflon (non-stick), Polystyrene, 
            Nylon-6,6, Bakelite, Natural rubber (isoprene polymer, cis-1,4-polyisoprene), Vulcanization (heating rubber with S, increases strength).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 15", "topic": "Polymers", "difficulty": "intermediate"
        },
    ]
    
    chunks = []
    for i, topic in enumerate(topics):
        chunk = {
            "id": create_chunk_id(topic["content"], "chemistry", i),
            "content": topic["content"].strip(),
            "metadata": {
                "source": "NCERT Chemistry",
                "subject": "chemistry",
                "class": topic["class"],
                "unit": topic["unit"],
                "chapter": topic["chapter"],
                "topic": topic["topic"],
                "difficulty": topic["difficulty"],
                "ncert_aligned": True
            },
            "quality_score": 0.95,
            "tokens": len(topic["content"].split())
        }
        chunks.append(chunk)
    
    return chunks


if __name__ == "__main__":
    print("Creating comprehensive chemistry chunks...")
    chunks = create_comprehensive_chemistry_chunks()
    print(f"Created {len(chunks)} chemistry chunks")
    
    output_dir = Path("vectorstore_data")
    output_dir.mkdir(exist_ok=True)
    
    output = {
        'subject': 'chemistry',
        'created_at': datetime.now().isoformat(),
        'total_chunks': len(chunks),
        'chunks': chunks
    }
    
    with open(output_dir / "chemistry_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to vectorstore_data/chemistry_chunks.json")
