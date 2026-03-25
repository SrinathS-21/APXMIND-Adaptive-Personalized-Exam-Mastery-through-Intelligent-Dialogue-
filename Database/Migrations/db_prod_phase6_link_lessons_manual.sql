-- Manual Lesson to Topic Linking
-- This script attempts to link lessons to topics based on keyword matching

-- Biology lessons
UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Cell Structure and Function'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Cell%'
        OR title LIKE '%Biomolecule%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Plant Physiology'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Photosynthesis%'
        OR title LIKE '%Respiration in Plants%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Human Physiology'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Human Physiology%'
        OR title LIKE '%Digestion%'
        OR title LIKE '%Circulatory%'
        OR title LIKE '%Respiratory%'
        OR title LIKE '%Nervous%'
        OR title LIKE '%Endocrine%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Reproduction'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Reproduction%'
        OR title LIKE '%Sexual%'
        OR title LIKE '%Human Reproduction%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Genetics and Evolution'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Genetics%'
        OR title LIKE '%Heredity%'
        OR title LIKE '%Evolution%'
        OR title LIKE '%DNA%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Ecology and Environment'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Ecology%'
        OR title LIKE '%Ecosystem%'
        OR title LIKE '%Environment%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Diversity in Living World'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Classification%'
        OR title LIKE '%Taxonomy%'
        OR title LIKE '%Kingdom%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Biotechnology and Its Applications'
        LIMIT 1
    )
WHERE
    subject_id = 1
    AND (
        title LIKE '%Biotechnology%'
        OR title LIKE '%Genetic Engineering%'
    )
    AND topic_id IS NULL;

-- Chemistry lessons
UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Some Basic Concepts of Chemistry'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Basic Concepts%'
        OR title LIKE '%Atoms%'
        OR title LIKE '%Molecules%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Structure of Atom'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Atomic Structure%'
        OR title LIKE '%Electron%'
        OR title LIKE '%Quantum%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Chemical Bonding and Molecular Structure'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Chemical Bonding%'
        OR title LIKE '%Bond%'
        OR title LIKE '%Molecule%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Thermodynamics'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Thermodynamics%'
        OR title LIKE '%Enthalpy%'
        OR title LIKE '%Entropy%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Equilibrium'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Equilibrium%'
        OR title LIKE '%Le Chatelier%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Electrochemistry'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Electrochemistry%'
        OR title LIKE '%Electrolysis%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Organic Chemistry Basics'
        LIMIT 1
    )
WHERE
    subject_id = 2
    AND (
        title LIKE '%Organic%'
        OR title LIKE '%Hydrocarbon%'
        OR title LIKE '%Alkane%'
        OR title LIKE '%Alkene%'
    )
    AND topic_id IS NULL;

-- Physics lessons
UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Kinematics'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Motion%'
        OR title LIKE '%Velocity%'
        OR title LIKE '%Acceleration%'
        OR title LIKE '%Kinematics%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Laws of Motion'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Newton%'
        OR title LIKE '%Force%'
        OR title LIKE '%Laws of Motion%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Work, Energy and Power'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Work%'
        OR title LIKE '%Energy%'
        OR title LIKE '%Power%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Gravitation'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Gravitation%'
        OR title LIKE '%Gravity%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Thermodynamics'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Thermodynamics%'
        OR title LIKE '%Heat%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Oscillations and Waves'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Wave%'
        OR title LIKE '%Oscillation%'
        OR title LIKE '%SHM%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Electrostatics'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Electrostatics%'
        OR title LIKE '%Electric Charge%'
        OR title LIKE '%Coulomb%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Current Electricity'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Current%'
        OR title LIKE '%Resistance%'
        OR title LIKE '%Ohm%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Magnetic Effects of Current and Magnetism'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Magnetic%'
        OR title LIKE '%Magnetism%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Optics'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Optics%'
        OR title LIKE '%Light%'
        OR title LIKE '%Lens%'
        OR title LIKE '%Mirror%'
    )
    AND topic_id IS NULL;

UPDATE lessons
SET
    topic_id = (
        SELECT id
        FROM topics
        WHERE
            name = 'Atoms and Nuclei'
        LIMIT 1
    )
WHERE
    subject_id = 3
    AND (
        title LIKE '%Atom%'
        OR title LIKE '%Nuclear%'
        OR title LIKE '%Radioactivity%'
    )
    AND topic_id IS NULL;

-- Verify results
SELECT 'Linked lessons:', COUNT(*)
FROM lessons
WHERE
    topic_id IS NOT NULL;

SELECT 'Unlinked lessons:', COUNT(*)
FROM lessons
WHERE
    topic_id IS NULL;