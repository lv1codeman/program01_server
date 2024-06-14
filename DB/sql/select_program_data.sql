-- SELECT 
--     p.program_id AS program_id,
--     p.program_name AS program_name,
--     c.category_id AS category_id,
--     c.category_name AS category_name,
--     d.domain_id AS domain_id,
--     d.domain_name AS domain_name,
--     s.subject_id AS subject_id,
--     s.subject_name AS subject_name,
--     co.course_id AS course_id
-- FROM 
--     programs p
--     INNER JOIN courses co ON p.program_id = co.program_id
--     INNER JOIN categories c ON co.category_id = c.category_id
--     LEFT JOIN domains d ON co.domain_id = d.domain_id
--     INNER JOIN subjects s ON co.subject_id = s.subject_id
-- WHERE p.program_id = 1;

SELECT 
    p.program_id AS program_id,
    p.program_name AS program_name,
    c.category_id AS category_id,
    c.category_name AS category_name,
    COALESCE(d.domain_id, 0) AS domain_id,
    COALESCE(d.domain_name, '0') AS domain_name,
    s.subject_id AS subject_id,
    s.subject_name AS subject_name,
    s.subject_sub_id AS subject_sub_id,
	s.subject_sys AS subject_sys,
	s.subject_unit AS subject_unit,
	s.subject_eng_name AS subject_eng_name,
    s.subject_credit AS subject_credit,
    s.subject_hour AS subject_hour
FROM 
    programs p
    INNER JOIN courses co ON p.program_id = co.program_id
    INNER JOIN categories c ON co.category_id = c.category_id
    LEFT JOIN domains d ON co.domain_id = d.domain_id
    INNER JOIN subjects s ON co.subject_id = s.subject_id;

