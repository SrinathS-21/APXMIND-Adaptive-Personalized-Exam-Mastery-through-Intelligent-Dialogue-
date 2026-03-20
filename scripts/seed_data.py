"""
Database Seed Script (Async SQLAlchemy 2.0)
=============================================

Populates the APXMIND database with NEET subjects and lessons.

Usage (from project root):
    python -m scripts.seed_data
"""

import asyncio
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from src.apxmind.core.config import Settings
from src.apxmind.db import session as db_session
from src.apxmind.db.models import Subject, Lesson


# ============================================================================
# SEED DATA — 3 subjects × many lessons each (comprehensive NEET syllabus)
# ============================================================================

SUBJECTS_DATA = [
    {
        "name": "biology",
        "display_name": "Biology",
        "description": "Study of living organisms — their structure, function, growth, and evolution",
        "icon": "dna",
        "color": "#4CAF50",
        "lessons": [
            {
                "title": "Cell: The Unit of Life",
                "description": "Cell structure, organelles, and the fundamental unit of biology",
                "difficulty": "easy",
                "order": 1,
                "estimated_time": 45,
                "topics": ["cell_structure", "cell_membrane", "organelles", "cell_theory"],
            },
            {
                "title": "Biomolecules",
                "description": "Carbohydrates, proteins, lipids, nucleic acids & enzymes",
                "difficulty": "medium",
                "order": 2,
                "estimated_time": 50,
                "topics": ["carbohydrates", "proteins", "lipids", "nucleic_acids", "enzymes"],
            },
            {
                "title": "Photosynthesis in Higher Plants",
                "description": "Light reactions, Calvin cycle, and factors affecting photosynthesis",
                "difficulty": "medium",
                "order": 3,
                "estimated_time": 60,
                "topics": ["light_reaction", "dark_reaction", "calvin_cycle", "chloroplast"],
            },
            {
                "title": "Respiration in Plants",
                "description": "Glycolysis, Krebs cycle, and electron transport chain",
                "difficulty": "hard",
                "order": 4,
                "estimated_time": 55,
                "topics": ["glycolysis", "krebs_cycle", "etc", "atp_synthesis"],
            },
            {
                "title": "Human Physiology — Digestion & Absorption",
                "description": "Digestive system, enzymes, absorption, and disorders",
                "difficulty": "medium",
                "order": 5,
                "estimated_time": 50,
                "topics": ["digestion", "enzymes", "absorption", "alimentary_canal"],
            },
            {
                "title": "Breathing and Exchange of Gases",
                "description": "Respiratory system, gas transport, and respiratory disorders",
                "difficulty": "medium",
                "order": 6,
                "estimated_time": 45,
                "topics": ["lungs", "gas_exchange", "respiratory_volumes", "disorders"],
            },
            {
                "title": "Body Fluids and Circulation",
                "description": "Blood composition, heart, circulatory pathways, and cardiac cycle",
                "difficulty": "medium",
                "order": 7,
                "estimated_time": 55,
                "topics": ["blood", "heart", "cardiac_cycle", "ecg", "blood_groups"],
            },
            {
                "title": "Excretory Products and Elimination",
                "description": "Kidney structure, urine formation, and osmoregulation",
                "difficulty": "hard",
                "order": 8,
                "estimated_time": 50,
                "topics": ["nephron", "urine_formation", "osmoregulation", "dialysis"],
            },
            {
                "title": "Neural Control and Coordination",
                "description": "Nervous system, reflex arc, brain, and sense organs",
                "difficulty": "hard",
                "order": 9,
                "estimated_time": 60,
                "topics": ["neuron", "reflex_arc", "brain", "sense_organs"],
            },
            {
                "title": "Genetics — Principles of Inheritance",
                "description": "Mendel's laws, linkage, crossing over, and sex determination",
                "difficulty": "medium",
                "order": 10,
                "estimated_time": 55,
                "topics": ["mendel", "linkage", "crossing_over", "sex_determination"],
            },
            {
                "title": "Molecular Basis of Inheritance",
                "description": "DNA structure, replication, transcription, and translation",
                "difficulty": "hard",
                "order": 11,
                "estimated_time": 65,
                "topics": ["dna", "replication", "transcription", "translation", "genetic_code"],
            },
            {
                "title": "Evolution",
                "description": "Origin of life, natural selection, and human evolution",
                "difficulty": "medium",
                "order": 12,
                "estimated_time": 45,
                "topics": ["natural_selection", "speciation", "human_evolution", "hardy_weinberg"],
            },
            {
                "title": "Human Health and Disease",
                "description": "Immunity, infectious diseases, cancer, and drugs",
                "difficulty": "medium",
                "order": 13,
                "estimated_time": 50,
                "topics": ["immunity", "antigens", "vaccines", "aids", "cancer"],
            },
            {
                "title": "Biotechnology — Principles and Processes",
                "description": "Genetic engineering, PCR, gel electrophoresis, and cloning",
                "difficulty": "hard",
                "order": 14,
                "estimated_time": 55,
                "topics": ["restriction_enzymes", "pcr", "gel_electrophoresis", "cloning"],
            },
            {
                "title": "Ecology — Organisms and Populations",
                "description": "Ecosystem dynamics, food chains, biogeochemical cycles",
                "difficulty": "medium",
                "order": 15,
                "estimated_time": 50,
                "topics": ["ecosystem", "food_chain", "nutrient_cycling", "succession"],
            },
        ],
    },
    {
        "name": "chemistry",
        "display_name": "Chemistry",
        "description": "Study of matter — its properties, composition, and transformations",
        "icon": "flask",
        "color": "#2196F3",
        "lessons": [
            {
                "title": "Some Basic Concepts of Chemistry",
                "description": "Mole concept, stoichiometry, and concentration terms",
                "difficulty": "easy",
                "order": 1,
                "estimated_time": 40,
                "topics": ["mole_concept", "stoichiometry", "molarity", "equivalent_weight"],
            },
            {
                "title": "Structure of Atom",
                "description": "Atomic models, quantum numbers, orbitals, and electronic configuration",
                "difficulty": "medium",
                "order": 2,
                "estimated_time": 50,
                "topics": ["atomic_models", "quantum_numbers", "orbitals", "electronic_configuration"],
            },
            {
                "title": "Chemical Bonding and Molecular Structure",
                "description": "Ionic, covalent, VSEPR theory, and hybridization",
                "difficulty": "medium",
                "order": 3,
                "estimated_time": 55,
                "topics": ["ionic_bonding", "covalent_bonding", "vsepr_theory", "hybridization"],
            },
            {
                "title": "Thermodynamics",
                "description": "Laws of thermodynamics, enthalpy, entropy, and Gibbs energy",
                "difficulty": "hard",
                "order": 4,
                "estimated_time": 60,
                "topics": ["first_law", "enthalpy", "entropy", "gibbs_energy", "hess_law"],
            },
            {
                "title": "Equilibrium",
                "description": "Chemical equilibrium, Le Chatelier's principle, ionic equilibrium",
                "difficulty": "medium",
                "order": 5,
                "estimated_time": 55,
                "topics": ["equilibrium_constant", "le_chatelier", "ph", "buffer_solutions"],
            },
            {
                "title": "Redox Reactions",
                "description": "Oxidation numbers, balancing redox reactions, electrochemical cells",
                "difficulty": "medium",
                "order": 6,
                "estimated_time": 45,
                "topics": ["oxidation_number", "balancing", "electrochemical_cells", "galvanic_cell"],
            },
            {
                "title": "Organic Chemistry — Basic Principles",
                "description": "IUPAC nomenclature, isomerism, and reaction mechanisms",
                "difficulty": "medium",
                "order": 7,
                "estimated_time": 65,
                "topics": ["nomenclature", "isomerism", "functional_groups", "reaction_mechanisms"],
            },
            {
                "title": "Hydrocarbons",
                "description": "Alkanes, alkenes, alkynes, and aromatic hydrocarbons",
                "difficulty": "medium",
                "order": 8,
                "estimated_time": 55,
                "topics": ["alkanes", "alkenes", "alkynes", "benzene", "aromaticity"],
            },
            {
                "title": "Solutions",
                "description": "Concentration, colligative properties, Raoult's law",
                "difficulty": "medium",
                "order": 9,
                "estimated_time": 50,
                "topics": ["molality", "colligative_properties", "raoults_law", "osmotic_pressure"],
            },
            {
                "title": "Electrochemistry",
                "description": "Nernst equation, conductivity, and electrolytic cells",
                "difficulty": "hard",
                "order": 10,
                "estimated_time": 55,
                "topics": ["nernst_equation", "conductivity", "electrolysis", "batteries"],
            },
            {
                "title": "Chemical Kinetics",
                "description": "Rate laws, order of reaction, Arrhenius equation",
                "difficulty": "hard",
                "order": 11,
                "estimated_time": 50,
                "topics": ["rate_law", "order", "arrhenius", "activation_energy"],
            },
            {
                "title": "Coordination Compounds",
                "description": "Werner's theory, nomenclature, isomerism, bonding in complexes",
                "difficulty": "hard",
                "order": 12,
                "estimated_time": 55,
                "topics": ["werner_theory", "nomenclature", "isomerism", "crystal_field_theory"],
            },
        ],
    },
    {
        "name": "physics",
        "display_name": "Physics",
        "description": "Study of matter, energy, motion, and fundamental forces of nature",
        "icon": "atom",
        "color": "#FF9800",
        "lessons": [
            {
                "title": "Physical World and Measurement",
                "description": "Units, dimensions, significant figures, and error analysis",
                "difficulty": "easy",
                "order": 1,
                "estimated_time": 35,
                "topics": ["units", "dimensions", "significant_figures", "errors"],
            },
            {
                "title": "Kinematics",
                "description": "Motion in a straight line, projectile motion, relative velocity",
                "difficulty": "medium",
                "order": 2,
                "estimated_time": 50,
                "topics": ["motion", "velocity", "acceleration", "projectile_motion"],
            },
            {
                "title": "Laws of Motion",
                "description": "Newton's laws, friction, circular motion, and momentum",
                "difficulty": "medium",
                "order": 3,
                "estimated_time": 55,
                "topics": ["newtons_laws", "friction", "circular_motion", "momentum"],
            },
            {
                "title": "Work, Energy and Power",
                "description": "Work-energy theorem, conservation of energy, and power",
                "difficulty": "medium",
                "order": 4,
                "estimated_time": 45,
                "topics": ["work", "energy", "power", "conservation"],
            },
            {
                "title": "Gravitation",
                "description": "Newton's law of gravitation, Kepler's laws, satellites",
                "difficulty": "medium",
                "order": 5,
                "estimated_time": 50,
                "topics": ["gravitation", "kepler", "satellites", "escape_velocity"],
            },
            {
                "title": "Mechanical Properties of Solids & Fluids",
                "description": "Stress, strain, elasticity, viscosity, Bernoulli's principle",
                "difficulty": "medium",
                "order": 6,
                "estimated_time": 55,
                "topics": ["stress", "strain", "viscosity", "bernoulli", "surface_tension"],
            },
            {
                "title": "Thermodynamics",
                "description": "Laws of thermodynamics, heat engines, entropy",
                "difficulty": "hard",
                "order": 7,
                "estimated_time": 60,
                "topics": ["first_law", "second_law", "heat_engines", "carnot_cycle"],
            },
            {
                "title": "Waves and Oscillations",
                "description": "SHM, wave motion, standing waves, Doppler effect",
                "difficulty": "medium",
                "order": 8,
                "estimated_time": 55,
                "topics": ["shm", "wave_motion", "standing_waves", "doppler_effect"],
            },
            {
                "title": "Electrostatics",
                "description": "Coulomb's law, electric field, potential, capacitors",
                "difficulty": "hard",
                "order": 9,
                "estimated_time": 60,
                "topics": ["electric_charge", "coulombs_law", "electric_field", "capacitors"],
            },
            {
                "title": "Current Electricity",
                "description": "Ohm's law, Kirchhoff's laws, Wheatstone bridge",
                "difficulty": "medium",
                "order": 10,
                "estimated_time": 55,
                "topics": ["ohms_law", "kirchhoff", "wheatstone", "potentiometer"],
            },
            {
                "title": "Magnetism and Moving Charges",
                "description": "Biot-Savart law, Ampere's law, magnetic materials",
                "difficulty": "hard",
                "order": 11,
                "estimated_time": 55,
                "topics": ["biot_savart", "ampere", "magnetic_force", "galvanometer"],
            },
            {
                "title": "Electromagnetic Induction",
                "description": "Faraday's law, Lenz's law, AC generator, transformers",
                "difficulty": "hard",
                "order": 12,
                "estimated_time": 55,
                "topics": ["faradays_law", "lenz_law", "ac_generator", "transformer"],
            },
            {
                "title": "Optics",
                "description": "Ray optics, wave optics, interference, and diffraction",
                "difficulty": "medium",
                "order": 13,
                "estimated_time": 60,
                "topics": ["reflection", "refraction", "interference", "diffraction"],
            },
            {
                "title": "Modern Physics",
                "description": "Photoelectric effect, atomic spectra, nuclear physics",
                "difficulty": "hard",
                "order": 14,
                "estimated_time": 60,
                "topics": ["photoelectric_effect", "bohr_model", "nuclear_fission", "radioactivity"],
            },
            {
                "title": "Semiconductor Electronics",
                "description": "p-n junction, diodes, transistors, and logic gates",
                "difficulty": "medium",
                "order": 15,
                "estimated_time": 50,
                "topics": ["semiconductors", "pn_junction", "transistors", "logic_gates"],
            },
        ],
    },
]


# ============================================================================
# ASYNC SEED LOGIC
# ============================================================================

async def seed_database():
    """Seed subjects and lessons using async SQLAlchemy."""
    settings = Settings()
    db_session.init_db_engine(settings)
    await db_session.create_tables()

    async with db_session._async_session_factory() as session:
        for subject_data in SUBJECTS_DATA:
            lessons_data = subject_data.pop("lessons")

            # Check if subject already exists
            existing = await session.execute(
                select(Subject).where(Subject.name == subject_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  ⚠  Subject '{subject_data['display_name']}' already exists — skipping")
                subject_data["lessons"] = lessons_data
                continue

            subject = Subject(**subject_data, total_lessons=len(lessons_data))
            session.add(subject)
            await session.flush()

            print(f"  ✅ {subject.display_name} ({len(lessons_data)} lessons)")

            for ld in lessons_data:
                lesson = Lesson(subject_id=subject.id, **ld)
                session.add(lesson)
                print(f"      • {lesson.title}")

            subject_data["lessons"] = lessons_data  # restore

        await session.commit()
        print("\n  ✅ Database seeded successfully!")


async def verify_seed():
    """Quick verification of seeded data."""
    async with db_session._async_session_factory() as session:
        result = await session.execute(select(Subject))
        subjects = result.scalars().all()
        total_lessons = 0
        for s in subjects:
            result2 = await session.execute(
                select(Lesson).where(Lesson.subject_id == s.id)
            )
            lessons = result2.scalars().all()
            total_lessons += len(lessons)
            print(f"  {s.display_name}: {len(lessons)} lessons")
        print(f"\n  Total: {len(subjects)} subjects, {total_lessons} lessons")


def main():
    print("\n" + "=" * 50)
    print("  APXMIND — Database Seed")
    print("=" * 50 + "\n")
    asyncio.run(seed_database())
    print()
    asyncio.run(verify_seed())
    print()


if __name__ == "__main__":
    main()
