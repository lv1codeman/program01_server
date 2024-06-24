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
*
FROM 
    program_structure ps
    INNER JOIN programs p ON p.program_id = ps.program_id
    INNER JOIN categories c ON ps.category_id = c.category_id
    LEFT JOIN domains d ON ps.domain_id = d.domain_id
    INNER JOIN subjects s ON ps.subject_sub_id = s.subject_sub_id;

