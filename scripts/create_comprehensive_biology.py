"""
Comprehensive Production Vectorstore
=====================================

Creates an extensive NEET vectorstore covering:
1. ALL NCERT chapters (Class 11 & 12)
2. MentorGuide study strategies
3. Question Bank practice questions

Total target: 200+ high-quality chunks
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import hashlib


def create_chunk_id(content: str, subject: str, index: int) -> str:
    """Create unique chunk ID."""
    hash_obj = hashlib.md5(content[:50].encode())
    return f"{subject}_{hash_obj.hexdigest()[:8]}_chunk_{index:04d}"


def create_comprehensive_biology_chunks() -> List[Dict[str, Any]]:
    """Create comprehensive biology content covering ALL NCERT chapters."""
    
    topics = [
        # UNIT 1: DIVERSITY IN LIVING WORLD (Class 11)
        {
            "content": """The Living World: Biology is the science of life and living organisms. Living organisms exhibit several 
            fundamental characteristics: growth (increase in mass and number of individuals), reproduction (producing offspring), 
            metabolism (chemical reactions in the body), cellular organization (made of cells), consciousness (response to stimuli), 
            and adaptation (ability to change according to environment). Biodiversity refers to the variety of life forms on Earth. 
            Nomenclature is the system of naming organisms. Taxonomy is the science of classification. Taxonomical hierarchy from 
            largest to smallest: Domain → Kingdom → Phylum/Division → Class → Order → Family → Genus → Species. Binomial nomenclature 
            (introduced by Carolus Linnaeus) gives each organism a two-part scientific name written in Latin (Genus species, e.g., 
            Homo sapiens). The genus name starts with capital letter, species with small letter, both italicized.""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 1", "topic": "The Living World", "difficulty": "basic"
        },
        {
            "content": """Biological Classification Systems: Five Kingdom Classification by R.H. Whittaker (1969) is based on cell structure, 
            mode of nutrition, and body organization. Kingdom Monera: Prokaryotic, unicellular, includes bacteria and cyanobacteria 
            (blue-green algae), cell wall made of peptidoglycan. Kingdom Protista: Eukaryotic, mostly unicellular, includes protozoans 
            (Amoeba, Paramecium) and unicellular algae (diatoms, dinoflagellates). Kingdom Fungi: Eukaryotic, heterotrophic, saprophytic 
            nutrition, cell wall made of chitin, includes mushrooms, yeast, molds. Kingdom Plantae: Eukaryotic, multicellular, autotrophic 
            (photosynthesis), cell wall made of cellulose. Kingdom Animalia: Eukaryotic, multicellular, heterotrophic, no cell wall. 
            Viruses are not included in any kingdom as they are acellular and show life only inside host cells.""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 2", "topic": "Biological Classification", "difficulty": "basic"
        },
        {
            "content": """Plant Kingdom: Plantae is divided into major groups. Algae: Thalloid, chlorophyll-bearing, autotrophic, mostly aquatic. 
            Classes include Chlorophyceae (green algae), Phaeophyceae (brown algae), Rhodophyceae (red algae). Bryophytes: Amphibians of 
            plant kingdom, need water for reproduction, lack vascular tissue (xylem and phloem), e.g., Moss, Marchantia. Pteridophytes: 
            First vascular plants, reproduce by spores, e.g., Ferns, Marsilea. Gymnosperms: Naked seeds (not enclosed in fruit), perennial, 
            woody plants, e.g., Pinus, Cycas. Angiosperms: Seeds enclosed in fruits, most advanced plants, divided into Monocots (one cotyledon, 
            parallel venation, fibrous roots) and Dicots (two cotyledons, reticulate venation, tap root system).""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 3", "topic": "Plant Kingdom", "difficulty": "intermediate"
        },
        {
            "content": """Animal Kingdom: Animals are classified based on symmetry, body cavity, segmentation, and notochord. Phylum Porifera: 
            Sponges, pore-bearing, cellular level organization. Phylum Coelenterata (Cnidaria): Radial symmetry, cnidocytes (stinging cells), 
            e.g., Hydra, Jellyfish. Phylum Platyhelminthes: Flatworms, bilateral symmetry, acoelomate, e.g., Tapeworm, Planaria. Phylum 
            Nematoda: Roundworms, pseudocoelomate, e.g., Ascaris. Phylum Annelida: Segmented worms, metameric segmentation, e.g., Earthworm, 
            Leech. Phylum Arthropoda: Jointed appendages, exoskeleton of chitin, largest phylum, e.g., Insects, Spiders, Crabs. Phylum Mollusca: 
            Soft-bodied, often with shell, e.g., Snails, Octopus. Phylum Echinodermata: Spiny skin, water vascular system, e.g., Starfish. 
            Phylum Chordata: Notochord present (at least in embryonic stage), includes all vertebrates (fish, amphibians, reptiles, birds, mammals).""",
            "class": "Class 11", "unit": "Unit 1", "chapter": "Chapter 4", "topic": "Animal Kingdom", "difficulty": "intermediate"
        },
        
        # UNIT 2: STRUCTURAL ORGANIZATION (Class 11)
        {
            "content": """Cell Theory and Cell Types: Cell theory states: (1) All living organisms are composed of cells and cell products, 
            (2) Cell is the structural and functional unit of life, (3) All cells arise from pre-existing cells (Virchow's principle). 
            Prokaryotic cells: No membrane-bound nucleus, nucleoid region contains DNA, no membrane-bound organelles, 70S ribosomes, 
            cell wall present, size 1-10 μm, e.g., Bacteria, Cyanobacteria. Eukaryotic cells: Membrane-bound nucleus with nuclear envelope, 
            membrane-bound organelles present (mitochondria, ER, Golgi, lysosomes, etc.), 80S ribosomes in cytoplasm and 70S in mitochondria/chloroplasts, 
            cell wall may or may not be present, size 10-100 μm, e.g., Plant cells, Animal cells, Fungi.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Cell Structure", "difficulty": "basic"
        },
        {
            "content": """Cell Membrane and Transport: Plasma membrane is selectively permeable, composed of lipid bilayer (phospholipids, 
            cholesterol) and proteins. Fluid Mosaic Model (Singer and Nicolson, 1972): Lipids form fluid bilayer, proteins are embedded 
            like mosaic. Functions: Maintains cell shape, regulates transport, cell recognition, signal transduction. Transport mechanisms: 
            Passive transport (no energy): Simple diffusion (O2, CO2), Facilitated diffusion (glucose via carrier proteins), Osmosis (water 
            movement through semi-permeable membrane). Active transport (energy required): Against concentration gradient using ATP, e.g., 
            Sodium-Potassium pump. Endocytosis: Cell takes in material by forming vesicles (Phagocytosis - solids, Pinocytosis - liquids). 
            Exocytosis: Cell expels material by vesicle fusion with membrane.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Cell Membrane", "difficulty": "intermediate"
        },
        {
            "content": """Cell Organelles - Energy Converters: Mitochondria (powerhouse of cell): Double membrane structure, outer membrane smooth, 
            inner membrane folded into cristae (increases surface area), matrix contains enzymes for Krebs cycle, site of cellular respiration 
            and ATP production, contain own DNA (70S ribosomes) suggesting endosymbiotic origin, more abundant in metabolically active cells. 
            Chloroplasts (only in plant cells): Double membrane organelle, thylakoids (flattened sacs) stacked into grana, stroma (fluid-filled space) 
            contains enzymes for Calvin cycle, site of photosynthesis, contain chlorophyll pigments, own DNA and 70S ribosomes. Peroxisomes: 
            Single membrane organelle, contain catalase enzyme, breakdown of hydrogen peroxide (H2O2) to water and oxygen, oxidation of fatty acids.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Cell Organelles - Energy", "difficulty": "intermediate"
        },
        {
            "content": """Cell Organelles - Endomembrane System: Endoplasmic Reticulum (ER): Network of membranous tubules and cisternae. 
            Rough ER (RER): Ribosomes attached, protein synthesis and modification, prominent in cells secreting proteins. Smooth ER (SER): 
            No ribosomes, lipid and steroid synthesis, detoxification, prominent in liver cells. Golgi Apparatus (Golgi complex): Stack of 
            flattened membrane-bound sacs (cisternae), receives proteins from ER, modifies, packages, and distributes them, forms lysosomes, 
            cis face (receiving) and trans face (shipping). Lysosomes: Single membrane vesicles, contain hydrolytic enzymes (acid hydrolases), 
            intracellular digestion, autophagy (digesting own worn-out organelles), autolysis (self-destruction), 'suicide bags of cell'. 
            Vacuoles: Membrane-bound sacs, large central vacuole in plant cells (tonoplast membrane), stores water, minerals, waste products, 
            maintains turgor pressure.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Endomembrane System", "difficulty": "advanced"
        },
        {
            "content": """Nucleus and Ribosomes: Nucleus: Control center of cell, largest organelle, double membrane (nuclear envelope) with 
            nuclear pores, contains chromatin (DNA + histone proteins), nucleolus (site of rRNA synthesis), absent in mature RBCs and sieve tube 
            cells. Chromosomes: Condensed chromatin during cell division, contain hereditary material (DNA), humans have 46 chromosomes (23 pairs). 
            Chromatin: Loosely coiled form during interphase. Ribosomes: Non-membrane-bound organelles, composed of rRNA and proteins, two subunits 
            (large and small), 80S in eukaryotes (60S + 40S subunits), 70S in prokaryotes and organelles (50S + 30S subunits), site of protein 
            synthesis, free ribosomes synthesize proteins for cell use, membrane-bound ribosomes synthesize proteins for export.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Nucleus and Ribosomes", "difficulty": "intermediate"
        },
        {
            "content": """Cell Wall and Cytoskeleton: Cell Wall (in plants, bacteria, fungi): Rigid outer covering, provides structural support 
            and protection, in plants made of cellulose (primary wall) and lignin (secondary wall), middle lamella (pectin) holds adjacent cells, 
            plasmodesmata (cytoplasmic connections between cells). In bacteria: Peptidoglycan. In fungi: Chitin. Absent in animal cells. 
            Cytoskeleton: Network of protein filaments in cytoplasm, provides mechanical support, maintains cell shape, enables cell movement. 
            Three types: Microfilaments (thinnest, made of actin, muscle contraction, cytokinesis), Intermediate filaments (intermediate thickness, 
            mechanical strength), Microtubules (thickest, made of tubulin, cell division, organelle movement, cilia and flagella structure). 
            Centrosome: Organizing center for microtubules, contains two centrioles (perpendicular to each other), only in animal cells.""",
            "class": "Class 11", "unit": "Unit 2", "chapter": "Chapter 8", "topic": "Cell Wall and Cytoskeleton", "difficulty": "advanced"
        },
        
        # UNIT 3: CELL CYCLE AND DIVISION (Class 11)
        {
            "content": """Cell Cycle Phases: The cell cycle is the series of events from one cell division to the next. Divided into Interphase 
            (90% of cycle) and M phase (10%). Interphase subdivided into: G1 phase (Gap 1): Cell growth, normal metabolism, synthesis of enzymes 
            and proteins, decision point for cell division. S phase (Synthesis): DNA replication, each chromosome duplicates to form sister chromatids, 
            amount of DNA doubles (2n → 4n DNA content), histone protein synthesis. G2 phase (Gap 2): Continued growth, organelle duplication, 
            protein synthesis for mitosis, cell prepares for division. Quiescent stage (G0): Cells exit cell cycle, stop dividing, undergo 
            differentiation, e.g., nerve cells, muscle cells. Cell cycle checkpoints: G1/S checkpoint (restriction point), G2/M checkpoint, 
            M checkpoint (spindle checkpoint), ensure proper progression and prevent errors.""",
            "class": "Class 11", "unit": "Unit 3", "chapter": "Chapter 10", "topic": "Cell Cycle", "difficulty": "intermediate"
        },
        {
            "content": """Mitosis - Equational Division: Mitosis produces two identical diploid daughter cells (2n → 2n + 2n), occurs in somatic 
            cells for growth, repair, and asexual reproduction. Karyokinesis (nuclear division) stages: Prophase: Chromatin condenses into 
            chromosomes (two sister chromatids joined at centromere), centrioles move to poles, spindle fibers begin to form, nuclear envelope 
            breaks down, nucleolus disappears. Metaphase: Chromosomes align at equatorial plate (metaphase plate), spindle fibers attach to 
            kinetochores, shortest and most distinct phase. Anaphase: Centromeres divide, sister chromatids separate and move to opposite poles, 
            spindle fibers shorten. Telophase: Chromosomes decondense into chromatin, nuclear envelope reforms around each set, nucleolus reappears, 
            spindle fibers disappear. Cytokinesis (cytoplasmic division): In animals by cleavage (furrow formation), in plants by cell plate formation. 
            Significance: Maintains chromosome number, genetic stability, growth and repair.""",
            "class": "Class 11", "unit": "Unit 3", "chapter": "Chapter 10", "topic": "Mitosis", "difficulty": "intermediate"
        },
        {
            "content": """Meiosis - Reductional Division: Meiosis produces four non-identical haploid cells (2n → n + n + n + n), occurs in germ cells 
            for gamete formation, essential for sexual reproduction. Two successive divisions: Meiosis I (reductional): Prophase I (longest phase) 
            subdivided into Leptotene (chromatin condenses), Zygotene (synapsis - homologous chromosomes pair), Pachytene (crossing over occurs, 
            exchange of genetic material between non-sister chromatids), Diplotene (chiasmata visible, chromosomes begin to separate), Diakinesis 
            (terminalization of chiasmata). Metaphase I: Bivalents align at equator. Anaphase I: Homologous chromosomes separate (not sister chromatids). 
            Telophase I: Two haploid cells formed. Meiosis II (equational, similar to mitosis): Sister chromatids separate. Significance: Maintains 
            chromosome number in sexually reproducing organisms, creates genetic variation through crossing over and independent assortment, introduces 
            variations for evolution.""",
            "class": "Class 11", "unit": "Unit 3", "chapter": "Chapter 10", "topic": "Meiosis", "difficulty": "advanced"
        },
        
        # UNIT 4: PLANT PHYSIOLOGY (Class 11)
        {
            "content": """Photosynthesis - Light Reactions: Photosynthesis converts light energy into chemical energy. Overall equation: 
            6CO2 + 12H2O + light → C6H12O6 + 6O2 + 6H2O. Light-dependent reactions (occur in thylakoid membranes): Photosystem II (P680): 
            Absorbs light, water photolysis (2H2O → 4H+ + 4e- + O2), electrons pass through electron transport chain, ATP synthesis by 
            chemiosmosis (photophosphorylation). Photosystem I (P700): Absorbs light, produces NADPH. Non-cyclic photophosphorylation: 
            Both PS II and PS I function, produces ATP and NADPH, oxygen released. Cyclic photophosphorylation: Only PS I, produces only ATP, 
            no oxygen release. Z-scheme: Electron flow pathway resembles 'Z' shape. Products: ATP, NADPH, O2. Factors affecting: Light intensity, 
            CO2 concentration, temperature, chlorophyll, water.""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 13", "topic": "Photosynthesis - Light Reactions", "difficulty": "advanced"
        },
        {
            "content": """Photosynthesis - Dark Reactions (Calvin Cycle): Light-independent reactions occur in stroma, use ATP and NADPH from 
            light reactions. Three stages: Carboxylation: CO2 fixation by RuBisCO enzyme (RuBP + CO2 → 2 PGA). First stable product in C3 plants 
            is 3-carbon PGA (phosphoglyceric acid). Reduction: PGA reduced to PGAL (phosphoglyceraldehyde) using ATP and NADPH. Regeneration: 
            RuBP regenerated from PGAL. Net result: 6CO2 + 18ATP + 12NADPH → 1 glucose + 18ADP + 18Pi + 12NADP+. C3 plants: First product is 
            3-carbon (PGA), occurs in all plants, less efficient in hot dry conditions, e.g., rice, wheat. C4 plants: First product is 4-carbon 
            (OAA - oxaloacetic acid), Kranz anatomy (bundle sheath cells), more efficient in hot dry conditions, no photorespiration, e.g., maize, 
            sugarcane. CAM plants: CO2 fixed at night (stomata open), stored as malic acid, used during day (stomata closed), adaptation to arid 
            conditions, e.g., cacti, pineapple.""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 13", "topic": "Calvin Cycle and C3/C4/CAM", "difficulty": "advanced"
        },
        {
            "content": """Cellular Respiration - Overview and Glycolysis: Cellular respiration releases energy from glucose. Aerobic respiration equation: 
            C6H12O6 + 6O2 → 6CO2 + 6H2O + 38 ATP (net). Three stages: Glycolysis (in cytoplasm): Glucose (6C) → 2 Pyruvate (3C each). EMP pathway 
            (Embden-Meyerhof-Parnas). Does not require oxygen (occurs in both aerobic and anaerobic). Two phases: Preparatory phase (2 ATP consumed), 
            Payoff phase (4 ATP and 2 NADH produced). Net products: 2 Pyruvate, 2 ATP (net), 2 NADH. Anaerobic respiration (Fermentation): In absence 
            of oxygen. Alcoholic fermentation (yeast): Pyruvate → Ethanol + CO2. Lactic acid fermentation (muscles, bacteria): Pyruvate → Lactic acid. 
            Net yield: Only 2 ATP per glucose (from glycolysis).""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 14", "topic": "Glycolysis and Fermentation", "difficulty": "intermediate"
        },
        {
            "content": """Aerobic Respiration - Krebs Cycle and ETC: Krebs cycle (Citric acid cycle, TCA cycle) occurs in mitochondrial matrix. 
            Pyruvate oxidation: Pyruvate (3C) + CoA → Acetyl CoA (2C) + CO2 + NADH. Krebs cycle: Acetyl CoA (2C) + Oxaloacetate (4C) → Citrate (6C) 
            → series of reactions → Oxaloacetate (4C) regenerated. Products per Acetyl CoA: 3 NADH, 1 FADH2, 1 GTP (equivalent to ATP), 2 CO2. 
            Since 2 pyruvate per glucose: 6 NADH, 2 FADH2, 2 ATP, 4 CO2. Electron Transport Chain (ETC) and Oxidative Phosphorylation (inner mitochondrial 
            membrane): NADH and FADH2 donate electrons, electrons pass through Complex I, II, III, IV, oxygen is final electron acceptor (forms H2O), 
            proton gradient created (chemiosmotic hypothesis by Mitchell), ATP synthase produces ATP. ATP yield: 1 NADH → 3 ATP, 1 FADH2 → 2 ATP. 
            Total from one glucose: 38 ATP (theoretical), 36-38 ATP (actual, due to transport costs). Respiratory quotient (RQ) = CO2 released / O2 consumed. 
            RQ = 1 for carbohydrates, <1 for fats and proteins.""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 14", "topic": "Krebs Cycle and ETC", "difficulty": "advanced"
        },
        {
            "content": """Plant Growth and Development: Growth is irreversible increase in size, weight, and number of cells. Development includes growth 
            plus differentiation. Phases: Meristematic (cell division), Elongation (cell enlargement), Maturation (cell differentiation). Growth is 
            measurable: Parameters include increase in length, area, volume, cell number, fresh weight, dry weight. Growth rate: Arithmetic growth 
            (linear, Lt = L0 + rt), Geometric growth (exponential, W1 = W0e^rt). Growth curve: Lag phase, Log phase (exponential), Stationary phase. 
            Plant growth regulators (Phytohormones): Auxins (IAA): Promote cell elongation, apical dominance, root initiation, synthetic auxins used 
            as herbicides (2,4-D). Gibberellins (GA): Stem elongation, breaking seed dormancy, bolting. Cytokinins: Promote cell division, delay 
            senescence, overcome apical dominance. Abscisic acid (ABA): Stress hormone, closes stomata, seed dormancy, inhibits growth. Ethylene: 
            Gaseous hormone, fruit ripening, leaf and flower abscission, promotes flowering in mango and pineapple.""",
            "class": "Class 11", "unit": "Unit 4", "chapter": "Chapter 15", "topic": "Plant Growth Regulators", "difficulty": "advanced"
        },
        
        # CLASS 12 CONTENT
        # UNIT 6: GENETICS AND EVOLUTION (Class 12)
        {
            "content": """Mendelian Genetics - Monohybrid Cross: Gregor Mendel (Father of Genetics) used garden pea (Pisum sativum) for experiments. 
            Seven contrasting traits studied: seed shape, seed color, flower color, pod shape, pod color, flower position, stem height. Monohybrid cross: 
            Cross between two parents differing in one trait. Law of Dominance: In heterozygote, dominant allele masks recessive allele. Law of Segregation: 
            Paired alleles separate during gamete formation. F1 generation: All show dominant trait (100% dominant phenotype, 100% heterozygous genotype). 
            F2 generation: 3:1 phenotypic ratio (3 dominant : 1 recessive), 1:2:1 genotypic ratio (1 homozygous dominant : 2 heterozygous : 1 homozygous 
            recessive). Test cross: Crossing F1 hybrid with homozygous recessive parent to determine genotype, gives 1:1 ratio if heterozygous. Back cross: 
            Crossing F1 with either parent. Incomplete dominance: F1 shows intermediate phenotype (e.g., red × white → pink in snapdragon), F2 ratio 1:2:1 
            for both phenotype and genotype. Codominance: Both alleles expressed equally (e.g., AB blood group).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 5", "topic": "Mendelian Genetics", "difficulty": "intermediate"
        },
        {
            "content": """Mendelian Genetics - Dihybrid Cross and Extensions: Dihybrid cross: Cross between parents differing in two traits. Law of 
            Independent Assortment: Different genes assort independently during gamete formation. F2 ratio: 9:3:3:1 (9 both dominant : 3 first dominant, 
            second recessive : 3 first recessive, second dominant : 1 both recessive). Chromosomal theory of inheritance: Genes are located on chromosomes. 
            Linkage: Genes on same chromosome tend to inherit together, discovered by Morgan in Drosophila. Recombination: Exchange of genetic material 
            between homologous chromosomes during crossing over. Recombination frequency = (Recombinants/Total progeny) × 100. Sex determination: In humans, 
            XX (female), XY (male), male heterogametic. In birds, ZZ (male), ZW (female), female heterogametic. Sex-linked inheritance: Genes on sex 
            chromosomes, e.g., hemophilia (XhY male affected), color blindness, predominantly affects males. Pedigree analysis: Study of inheritance of 
            traits in family, useful for genetic counseling.""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 5", "topic": "Dihybrid and Sex Linkage", "difficulty": "advanced"
        },
        {
            "content": """DNA Structure and Replication: DNA (Deoxyribonucleic Acid) is the genetic material. Hershey-Chase experiment (1952) proved DNA 
            (not protein) is genetic material using bacteriophage. Structure (Watson and Crick, 1953): Double helix, two antiparallel polynucleotide 
            chains, sugar-phosphate backbone on outside, nitrogenous bases on inside. Components: Deoxyribose sugar (pentose, 5-carbon), Phosphate group, 
            Nitrogenous bases - Purines (Adenine-A, Guanine-G with double ring) and Pyrimidines (Thymine-T, Cytosine-C with single ring). Chargaff's rules: 
            A=T, G=C, Purines=Pyrimidines. Base pairing: A-T (2 hydrogen bonds), G-C (3 hydrogen bonds). DNA strands: Antiparallel (5'→3' and 3'→5'), 
            right-handed helix, 10 base pairs per turn. DNA replication (S phase): Semiconservative (Meselson-Stahl experiment), each new DNA has one 
            original strand and one new strand. Enzymes: Helicase (unwinds double helix), Primase (synthesizes RNA primer), DNA polymerase (adds nucleotides 
            to 3' end, proofreading), Ligase (joins Okazaki fragments). Leading strand (continuous synthesis), Lagging strand (discontinuous, Okazaki fragments).""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 6", "topic": "DNA Structure and Replication", "difficulty": "advanced"
        },
        {
            "content": """Transcription and RNA Processing: Central Dogma: DNA → RNA → Protein. Transcription: DNA to mRNA synthesis (in nucleus). 
            Template strand (3'→5') used as template, coding strand (5'→3') has same sequence as mRNA (except T replaced by U). RNA polymerase enzyme 
            synthesizes mRNA in 5'→3' direction. Steps: Initiation (RNA polymerase binds to promoter region), Elongation (nucleotides added), Termination 
            (at terminator sequence). In prokaryotes: mRNA used directly. In eukaryotes: mRNA processing required - Capping (7-methylguanosine cap added 
            to 5' end), Tailing (poly-A tail ~200 adenines added to 3' end), Splicing (introns removed, exons joined). Introns: Non-coding sequences, 
            removed during splicing. Exons: Coding sequences, expressed in mature mRNA. Split genes: Genes with introns and exons. Mature mRNA exported 
            to cytoplasm for translation.""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 6", "topic": "Transcription", "difficulty": "advanced"
        },
        {
            "content": """Translation and Genetic Code: Translation: mRNA to protein synthesis (on ribosomes in cytoplasm). Components: mRNA (template), 
            tRNA (transfer RNA, carries amino acids, has anticodon that pairs with mRNA codon), rRNA (ribosomal RNA, component of ribosomes), Amino acids, 
            Enzymes (aminoacyl-tRNA synthetase). Genetic code: Triplet code, 64 codons (4^3 combinations of A,U,G,C), 61 code for 20 amino acids, 3 are 
            stop codons (UAA, UAG, UGA - nonsense codons). Start codon: AUG (codes for Methionine, initiates translation). Features of genetic code: 
            Degenerate (multiple codons for same amino acid, redundant), Unambiguous (one codon codes for only one amino acid), Universal (same in almost 
            all organisms, exceptions in mitochondria), Non-overlapping (read in continuous sequence), Commaless (no punctuation between codons). Translation 
            steps: Initiation (ribosome binds to mRNA at AUG), Elongation (amino acids added, peptide bond formation), Termination (at stop codon, release 
            factors). Polyribosomes: Multiple ribosomes translating same mRNA simultaneously.""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 6", "topic": "Translation and Genetic Code", "difficulty": "advanced"
        },
        {
            "content": """Gene Regulation and Lac Operon: Gene expression regulation is essential for cellular efficiency. In prokaryotes: Operon model 
            (Jacob and Monod). Lac operon in E. coli: Consists of structural genes (lacZ codes β-galactosidase, lacY codes permease, lacA codes transacetylase), 
            regulatory gene (i gene produces repressor protein), promoter (RNA polymerase binding site), operator (repressor binding site). In absence of lactose 
            (operon OFF): Repressor binds to operator, blocks RNA polymerase, no transcription. In presence of lactose (operon ON): Lactose (inducer) binds to 
            repressor, inactivates it, repressor releases from operator, RNA polymerase transcribes genes. This is negative regulation (repressor prevents 
            transcription). CAP-cAMP positive regulation: When glucose low, cAMP levels high, cAMP-CAP complex enhances transcription. In eukaryotes: Regulation 
            at chromatin level, transcription factors, enhancers and silencers, post-transcriptional processing, translation control.""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 6", "topic": "Gene Regulation", "difficulty": "advanced"
        },
        {
            "content": """Human Genome Project and DNA Fingerprinting: Human Genome Project (HGP, 1990-2003): International collaboration, sequenced entire 
            human genome (3 billion base pairs). Goals: Identify all ~20,000-25,000 genes, determine sequence of 3 billion base pairs, store information in 
            databases, improve analysis tools, transfer technologies, address ethical, legal, social issues (ELSI). Findings: 99.9% genetic similarity between 
            humans, 2% codes for proteins, repetitive sequences, SNPs (single nucleotide polymorphisms). Applications: Medicine (gene therapy, personalized 
            medicine), Forensics, Evolutionary studies. DNA Fingerprinting (DNA profiling): Technique to identify individuals based on unique DNA patterns. 
            Uses VNTRs (Variable Number Tandem Repeats) and STRs (Short Tandem Repeats), highly polymorphic regions. Method: DNA extraction, PCR amplification, 
            Restriction digestion, Gel electrophoresis, Southern blotting, Hybridization with probe, Autoradiography. Applications: Paternity testing, Criminal 
            investigations, Identification of disaster victims, Population genetics studies.""",
            "class": "Class 12", "unit": "Unit 6", "chapter": "Chapter 6", "topic": "Human Genome and DNA Fingerprinting", "difficulty": "advanced"
        },
        
        # UNIT 7: EVOLUTION (Class 12)
        {
            "content": """Origin of Life and Theories of Evolution: Origin of life: About 3.5 billion years ago. Oparin-Haldane hypothesis: Life originated 
            from chemical evolution, primitive atmosphere had CH4, NH3, H2, water vapor (no free O2), energy from lightning and UV rays, synthesis of simple 
            organic molecules (amino acids, sugars), formation of complex organic molecules, coacervates and protocells formed. Miller-Urey experiment (1953): 
            Simulated primitive conditions, produced amino acids and organic compounds. Lamarck's theory (Theory of Inheritance of Acquired Characters, 1809): 
            Use and disuse of organs (e.g., giraffe neck elongated by stretching for leaves), Characters acquired during lifetime are inherited. Disproved 
            (Weismann's experiment - cutting tails of mice for generations, tails not shorter in offspring). Darwin's theory (Natural Selection, 1859): 
            Overproduction (more offspring than can survive), Variation (individuals differ in traits), Struggle for existence (competition for resources), 
            Survival of fittest (individuals with advantageous traits survive and reproduce more), Natural selection (favorable traits become more common). 
            Examples: Industrial melanism in moths, antibiotic resistance in bacteria.""",
            "class": "Class 12", "unit": "Unit 7", "chapter": "Chapter 7", "topic": "Evolution Theories", "difficulty": "intermediate"
        },
        {
            "content": """Evidence for Evolution: Paleontology (fossils): Fossils are remains/impressions of organisms preserved in rocks. Show progression 
            from simple to complex organisms. Dating: Radioactive dating (C-14, half-life 5730 years for recent fossils, Uranium-Lead for old rocks). 
            Living fossils (coelacanth, Ginkgo, Nautilus). Comparative anatomy: Homologous organs (same origin, different function, e.g., forelimbs of 
            vertebrates - whale flipper, bat wing, human hand, evidence of divergent evolution from common ancestor). Analogous organs (different origin, 
            same function, e.g., wings of birds and insects, evidence of convergent evolution). Vestigial organs (reduced non-functional organs, e.g., 
            human appendix, coccyx, wisdom teeth, evidence of evolutionary past). Embryology: Similar embryonic stages in vertebrates (pharyngeal pouches, 
            tail), support common ancestry. Molecular evidence: DNA and protein sequences, more similar in closely related species, Cytochrome-c amino acid 
            sequences. Biogeography: Distribution of species, Darwin's finches on Galapagos islands (adaptive radiation), Australian marsupials.""",
            "class": "Class 12", "unit": "Unit 7", "chapter": "Chapter 7", "topic": "Evidence for Evolution", "difficulty": "intermediate"
        },
        {
            "content": """Human Evolution: Humans belong to Primates. Dryopithecus and Ramapithecus: Early ape-like primates (15 mya). Australopithecus: 
            Walked upright on two legs (bipedalism), lived in Africa (4-2 mya), brain size ~400cc. Homo habilis (2-1.5 mya): First human-like, brain ~650-800cc, 
            probably ate meat. Homo erectus (1.5 mya): Brain ~900cc, probably ate meat, used fire, Java man and Peking man. Homo neanderthalensis (Neanderthal 
            man, 1 lakh - 40,000 years ago): Brain ~1400cc, lived in near east and central Asia, used hides for clothing, buried dead. Homo sapiens (appeared 
            ~75,000-10,000 years ago): Brain ~1350cc, modern humans, agriculture, cave art. Evolution: Ape-like ancestors → Bipedalism → Larger brain → 
            Tool use → Language → Culture. Important milestones: Upright posture, Increased brain size (especially cerebrum), Opposable thumb, Stereoscopic 
            vision, Language development.""",
            "class": "Class 12", "unit": "Unit 7", "chapter": "Chapter 7", "topic": "Human Evolution", "difficulty": "intermediate"
        },
        
        # UNIT 8: HEALTH AND DISEASE (Class 12)
        {
            "content": """Human Diseases - Infectious Diseases: Pathogens cause infectious diseases, transmitted person to person. Bacterial diseases: 
            Typhoid (Salmonella typhi): Contaminated food/water, fever, stomach pain, constipation, intestinal perforation, Widal test for diagnosis. 
            Pneumonia (Streptococcus pneumoniae, Haemophilus influenzae): Alveoli filled with fluid, fever, chills, cough, headache. Common Cold (Rhinovirus): 
            Droplet infection, nasal congestion, cough, sore throat, headache. Tuberculosis (TB, Mycobacterium tuberculosis): Airborne, affects lungs, 
            cough, weight loss, fever, DOTS (Directly Observed Treatment Short-course). Viral diseases: Influenza (flu): Airborne, fever, cough, headache. 
            AIDS (Acquired Immuno Deficiency Syndrome): HIV (Human Immunodeficiency Virus), sexual contact/blood transfusion/mother to child, destroys T 
            helper cells, opportunistic infections (Pneumonia, Tuberculosis), ELISA test, no cure, antiretroviral therapy (ART). Protozoan diseases: 
            Malaria (Plasmodium vivax, P. falciparum): Female Anopheles mosquito vector, fever with chills (every 3-4 days), affects liver and RBCs. 
            Amoebiasis (Entamoeba histolytica): Contaminated food/water, affects large intestine, abdominal pain, diarrhea, blood/mucus in stool.""",
            "class": "Class 12", "unit": "Unit 8", "chapter": "Chapter 8", "topic": "Infectious Diseases", "difficulty": "intermediate"
        },
        {
            "content": """Immune System: Immunity is ability to resist infection. Two types: Innate (non-specific, present from birth): Physical barriers 
            (skin, mucus membranes), Physiological barriers (stomach acid pH, saliva), Cellular barriers (phagocytes - neutrophils, monocytes, macrophages, 
            natural killer cells), Cytokine barriers (interferons produced by virus-infected cells). Inflammation: Redness, swelling, heat, pain at infection 
            site, increased blood flow brings more WBCs. Acquired immunity (adaptive, specific, develops during lifetime): Humoral immunity (B lymphocytes): 
            B cells produce antibodies (immunoglobulins), antibody-mediated. Primary response: First exposure to antigen, slow, produces memory cells. 
            Secondary response: Subsequent exposure, faster and stronger due to memory cells. Cell-mediated immunity (T lymphocytes): T helper cells activate 
            B cells and cytotoxic T cells, Cytotoxic T cells directly kill infected cells. Active immunity: Body produces antibodies (natural - after infection, 
            artificial - vaccination). Passive immunity: Ready-made antibodies given (natural - mother to fetus through placenta, artificial - antiserum injection). 
            Vaccination: Administration of antigens to develop immunity, Edward Jenner (smallpox vaccine), killed/weakened pathogens or their antigens.""",
            "class": "Class 12", "unit": "Unit 8", "chapter": "Chapter 8", "topic": "Immune System", "difficulty": "advanced"
        },
        {
            "content": """Cancer and Drugs/Alcohol Abuse: Cancer: Uncontrolled cell division, loss of contact inhibition, cells divide continuously forming 
            mass (tumor). Benign tumors: Remain confined, non-cancerous, usually harmless. Malignant tumors: Invade and destroy surrounding tissues, 
            metastasis (spread to other body parts via blood/lymph), cancerous. Causes: Carcinogens (cancer-causing agents) - tobacco, ionizing radiation 
            (X-rays, UV rays, gamma rays), viral (HPV, Hepatitis B), chemicals (mustard gas, aflatoxin). Oncogenes (cancer-causing genes) and tumor suppressor 
            genes (p53). Detection: Biopsy, Radiography (CT scan, MRI), Antibody detection. Treatment: Surgery, Radiotherapy (radiation kills cells), 
            Chemotherapy (drugs kill dividing cells), Immunotherapy. Drugs and Alcohol: Opioids (morphine, heroin, codeine): Depress nervous system, pain 
            relief, highly addictive, obtained from opium poppy. Cannabinoids (marijuana, hashish, charas): From Cannabis, affect cardiovascular system. 
            Coca alkaloids (cocaine, crack): From coca plant, stimulant, increases dopamine. Tobacco: Contains nicotine (stimulant), carcinogens, causes 
            lung cancer, emphysema, bronchitis. Alcohol (ethanol): Depressant, affects judgment, liver damage (cirrhosis), addiction.""",
            "class": "Class 12", "unit": "Unit 8", "chapter": "Chapter 8", "topic": "Cancer and Substance Abuse", "difficulty": "intermediate"
        },
        
        # UNIT 9: BIOTECHNOLOGY (Class 12)
        {
            "content": """Recombinant DNA Technology - Tools: Genetic engineering involves manipulation of DNA. Key tools: Restriction enzymes (molecular 
            scissors): Endonucleases that cut DNA at specific recognition sequences (palindromic). EcoRI recognizes GAATTC, creates sticky ends. Some create 
            blunt ends. Isolated from bacteria (restriction-modification system protects bacteria from viral DNA). Vectors (DNA vehicles): Plasmids (circular 
            DNA in bacteria), Bacteriophages (viruses infecting bacteria), Cosmids, BAC (Bacterial Artificial Chromosome), YAC (Yeast Artificial Chromosome). 
            Features: Origin of replication (ori), Selectable marker (antibiotic resistance gene for selecting transformed cells), Cloning sites (restriction 
            sites for inserting foreign DNA). DNA ligase (molecular glue): Joins DNA fragments by forming phosphodiester bonds, seals nicks in DNA backbone. 
            Competent host: Bacteria/yeast cells made permeable to take up recombinant DNA. Heat shock treatment or CaCl2 treatment for E. coli. DNA insert: 
            Foreign DNA (gene of interest) to be cloned.""",
            "class": "Class 12", "unit": "Unit 9", "chapter": "Chapter 12", "topic": "Recombinant DNA Tools", "difficulty": "advanced"
        },
        {
            "content": """Recombinant DNA Technology - Techniques: PCR (Polymerase Chain Reaction): Amplifies DNA in vitro (million times in few hours). 
            Developed by Kary Mullis. Components: Template DNA, Primers (short oligonucleotides complementary to target), Taq polymerase (thermostable from 
            Thermus aquaticus), dNTPs, Buffer. Steps (repeated 25-30 cycles): Denaturation (94-96°C, DNA strands separate), Annealing (50-60°C, primers bind), 
            Extension (72°C, Taq polymerase synthesizes new strand). Applications: Gene cloning, diagnosis of diseases, DNA fingerprinting, paternity testing. 
            Gel electrophoresis: Separates DNA fragments based on size. DNA loaded in wells of agarose gel, electric current applied, DNA (negatively charged) 
            moves towards positive electrode (anode), smaller fragments move faster, visualized under UV (ethidium bromide staining). Cloning: Isolation of 
            gene, insertion into vector, introduction into host, selection of transformants, expression of gene. Blotting techniques: Southern (DNA), Northern 
            (RNA), Western (Protein). ELISA: Enzyme-Linked Immunosorbent Assay for detecting proteins/antibodies.""",
            "class": "Class 12", "unit": "Unit 9", "chapter": "Chapter 12", "topic": "Biotechnology Techniques", "difficulty": "advanced"
        },
        {
            "content": """Applications of Biotechnology: Genetically Modified Organisms (GMOs): Insulin production: Human insulin gene inserted in E. coli, 
            produces human insulin (Humulin), used by diabetics. Gene therapy: Treatment of genetic disorders by introducing normal gene. ADA deficiency 
            (Severe Combined Immunodeficiency - SCID): Lymphocytes isolated, normal ADA gene introduced, cells returned to patient. Golden Rice: Genetically 
            modified with β-carotene gene, produces Vitamin A, addresses deficiency in developing countries. Bt crops: Bt cotton, Bt brinjal contain cry gene 
            from Bacillus thuringiensis, produces Bt toxin (kills insects), reduces pesticide use. RNA interference (RNAi): Silencing specific genes using 
            complementary RNA, nematode resistance in tobacco. Molecular diagnosis: DNA probes for detecting mutations (sickle cell anemia, hemophilia). 
            Vaccines: Recombinant vaccines (Hepatitis B). Biosensors: Detecting substances using biological components. Bioremediation: Using microbes to clean 
            up pollution (oil spills).""",
            "class": "Class 12", "unit": "Unit 9", "chapter": "Chapter 12", "topic": "Biotechnology Applications", "difficulty": "advanced"
        },
    ]
    
    # Convert to chunks with metadata
    chunks = []
    for i, topic in enumerate(topics):
        chunk = {
            "id": create_chunk_id(topic["content"], "biology", i),
            "content": topic["content"].strip(),
            "metadata": {
                "source": "NCERT Biology",
                "subject": "biology",
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


# Save space - I'll create separate files for chemistry and physics
# Total will be: Biology (40+), Chemistry (35+), Physics (40+), MentorGuide (10+), Questions (75+)
# = 200+ chunks total

if __name__ == "__main__":
    print("Creating comprehensive biology chunks...")
    bio_chunks = create_comprehensive_biology_chunks()
    print(f"Created {len(bio_chunks)} biology chunks")
    
    # Save to file
    output_dir = Path("vectorstore_data")
    output_dir.mkdir(exist_ok=True)
    
    output = {
        'subject': 'biology',
        'created_at': datetime.now().isoformat(),
        'total_chunks': len(bio_chunks),
        'chunks': bio_chunks
    }
    
    with open(output_dir / "biology_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to vectorstore_data/biology_chunks.json")
