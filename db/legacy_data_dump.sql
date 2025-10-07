--
-- PostgreSQL database dump
--

\restrict kzWqRDxLwRKbs0YYf4Z5M9Xfb6gvYaOLbgak3WOjkdMxOlWw4rcXMWduILlhs8h

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: basel_business_lines; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.basel_business_lines (id, name, description, parent_id) FROM stdin;
1	Retail Banking	Retail banking business line	\N
2	Wholesale Banking	Wholesale / Corporate banking	\N
3	Treasury	Treasury and Markets	\N
4	Payments	Payments and Cards	\N
5	IT & Operations	IT and operations services	\N
6	Human Resources	HR and recruitment	\N
7	Wealth Management	Wealth management	\N
\.


--
-- Data for Name: basel_event_types; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.basel_event_types (id, name, description, parent_id) FROM stdin;
1	Internal Fraud	Internal fraud (staff, management)	\N
2	External Fraud	External fraud (clients, third parties)	\N
3	Employment Practices & Workplace Safety	Employment practices and workplace safety	\N
4	Clients, Products & Business Practices	Client/product problems and practices	\N
5	Business Disruption & System Failures	IT outages, security incidents, system failures	\N
6	Execution, Delivery & Process Management	Execution / processing failures	\N
7	Damage to Physical Assets	Loss / damage of physical assets	\N
\.


--
-- Data for Name: business_units; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.business_units (id, name, parent_id) FROM stdin;
1	Wholesale	\N
2	Retail	\N
3	Operations	\N
4	Risk Management	\N
5	IT	\N
6	Fraud Unit	\N
7	InfoSec	\N
8	Group ORM	\N
9	Audit	\N
\.


--
-- Data for Name: business_processes; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.business_processes (id, name, parent_id, business_unit_id) FROM stdin;
1	Trade Finance	\N	1
2	Credit Cards	\N	2
3	Reconciliation	\N	3
4	Risk Assessment	\N	4
5	Core Banking Systems	\N	5
6	Fraud Investigation	\N	6
7	Security Monitoring	\N	7
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.roles (id, name, description) FROM stdin;
1	Employee	Regular reporting employee
2	Manager	First-line manager / supervisor
3	Risk Officer	Operational Risk / ORM (2nd line)
4	IT Admin	IT operations
5	InfoSec	Information Security team
6	Fraud Investigator	Fraud Investigation Unit
7	Group ORM	Group-level ORM team
8	Audit/Admin	Audit or system admin
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.users (id, username, email, full_name, business_unit_id, role_id, manager_id, external_id, external_source, is_active, created_at) FROM stdin;
1	bob_mgr	bob.manager@bank.com	Bob Manager	2	2	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
2	wh_mgr	wh.manager@bank.com	Wendy Wholesale	1	2	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
3	carol_orm	carol.orm@bank.com	Carol ORM	4	3	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
4	eve_infosec	eve.infosec@bank.com	Eve InfoSec	7	5	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
5	frank_fraud	frank.fraud@bank.com	Frank Fraud	6	6	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
6	greg_grouporm	greg.grouporm@bank.com	Greg GroupORM	8	7	\N	\N	\N	t	2025-10-04 22:43:47.407122+00
7	alice_emp	alice@bank.com	Alice Employee	2	1	1	\N	\N	t	2025-10-04 22:43:47.408425+00
8	henry_wh_emp	henry@bank.com	Henry Wholesale	1	1	2	\N	\N	t	2025-10-04 22:43:47.408425+00
9	dave_it	dave.it@bank.com	Dave IT	5	4	\N	\N	\N	t	2025-10-04 22:43:47.408425+00
\.


--
-- Data for Name: controls; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.controls (id, name, description, reference_doc, effectiveness, business_process_id, created_by, created_at, updated_at) FROM stdin;
1	Daily Reconciliation	Daily reconciliation of accounts	\N	4	3	8	2025-10-04 22:43:47.415736+00	\N
2	Firewall Monitoring	Firewall monitoring and patching	\N	3	5	9	2025-10-04 22:43:47.415736+00	\N
\.


--
-- Data for Name: incident_audit; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_audit (id, incident_id, operation_type, changed_by, changed_at, old_data, new_data) FROM stdin;
1	1	INSERT	\N	2025-10-04 22:43:47.410749+00	\N	{"id": 1, "notes": null, "title": "Large Trading Loss", "end_time": null, "closed_at": null, "closed_by": null, "near_miss": false, "status_id": 1, "created_at": "2025-09-22T22:43:47.410749+00:00", "deleted_at": null, "deleted_by": null, "product_id": null, "start_time": null, "assigned_to": null, "description": "Large trading loss due to failed hedge; large material loss > $1M", "reported_by": 8, "draft_due_at": "2025-09-27T22:43:47.410749+00:00", "validated_at": null, "validated_by": null, "currency_code": "USD", "discovered_at": "2025-09-22T22:43:47.410749+00:00", "review_due_at": null, "net_loss_amount": null, "recovery_amount": 0.00, "business_unit_id": 1, "gross_loss_amount": 2000000.00, "validation_due_at": null, "basel_event_type_id": 4, "business_process_id": 1, "basel_business_line_id": 2}
2	2	INSERT	\N	2025-10-04 22:43:47.413614+00	\N	{"id": 2, "notes": null, "title": "Retail IT Outage", "end_time": null, "closed_at": null, "closed_by": null, "near_miss": false, "status_id": 1, "created_at": "2025-10-02T22:43:47.413614+00:00", "deleted_at": null, "deleted_by": null, "product_id": 2, "start_time": null, "assigned_to": null, "description": "Outage of POS and web payment in Retail store cluster; needs InfoSec attention", "reported_by": 7, "draft_due_at": "2025-10-07T22:43:47.413614+00:00", "validated_at": null, "validated_by": null, "currency_code": "USD", "discovered_at": "2025-10-02T22:43:47.413614+00:00", "review_due_at": null, "net_loss_amount": null, "recovery_amount": 0.00, "business_unit_id": 2, "gross_loss_amount": 50000.00, "validation_due_at": null, "basel_event_type_id": 5, "business_process_id": 2, "basel_business_line_id": 1}
3	3	INSERT	\N	2025-10-04 22:43:47.414504+00	\N	{"id": 3, "notes": null, "title": "Credit Card Fraud", "end_time": null, "closed_at": null, "closed_by": null, "near_miss": false, "status_id": 1, "created_at": "2025-09-23T22:43:47.414504+00:00", "deleted_at": null, "deleted_by": null, "product_id": 2, "start_time": null, "assigned_to": null, "description": "Multiple suspicious transactions observed on several cards; preliminary ticket", "reported_by": 7, "draft_due_at": "2025-09-28T22:43:47.414504+00:00", "validated_at": null, "validated_by": null, "currency_code": "USD", "discovered_at": "2025-09-23T22:43:47.414504+00:00", "review_due_at": null, "net_loss_amount": null, "recovery_amount": 0.00, "business_unit_id": 2, "gross_loss_amount": 25000.00, "validation_due_at": null, "basel_event_type_id": 2, "business_process_id": 2, "basel_business_line_id": 1}
4	4	INSERT	\N	2025-10-04 22:43:47.415151+00	\N	{"id": 4, "notes": null, "title": "Reconciliation Error", "end_time": null, "closed_at": null, "closed_by": null, "near_miss": false, "status_id": 2, "created_at": "2025-09-30T22:43:47.415151+00:00", "deleted_at": null, "deleted_by": null, "product_id": null, "start_time": null, "assigned_to": 2, "description": "Daily reconciliation mismatch: suspected human error", "reported_by": 8, "draft_due_at": "2025-10-05T22:43:47.415151+00:00", "validated_at": null, "validated_by": null, "currency_code": "USD", "discovered_at": "2025-09-30T22:43:47.415151+00:00", "review_due_at": null, "net_loss_amount": null, "recovery_amount": 0.00, "business_unit_id": 3, "gross_loss_amount": 0.00, "validation_due_at": null, "basel_event_type_id": null, "business_process_id": 3, "basel_business_line_id": null}
\.


--
-- Data for Name: incident_status_ref; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_status_ref (id, code, name) FROM stdin;
1	DRAFT	Draft
2	PENDING_REVIEW	Pending Manager Review
3	PENDING_VALIDATION	Pending Risk Validation
4	VALIDATED	Validated
5	CLOSED	Closed
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.products (id, name, business_unit_id) FROM stdin;
1	Corporate Loan	1
2	Credit Card	2
3	Payments Service	\N
\.


--
-- Data for Name: incidents; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incidents (id, title, description, start_time, end_time, discovered_at, created_at, business_unit_id, business_process_id, product_id, basel_event_type_id, basel_business_line_id, status_id, reported_by, assigned_to, validated_by, validated_at, closed_by, closed_at, draft_due_at, review_due_at, validation_due_at, deleted_at, deleted_by, gross_loss_amount, recovery_amount, net_loss_amount, currency_code, near_miss, notes) FROM stdin;
1	Large Trading Loss	Large trading loss due to failed hedge; large material loss > $1M	\N	\N	2025-09-22 22:43:47.410749+00	2025-09-22 22:43:47.410749+00	1	1	\N	4	2	1	8	\N	\N	\N	\N	\N	2025-09-27 22:43:47.410749+00	\N	\N	\N	\N	2000000.00	0.00	\N	USD	f	\N
2	Retail IT Outage	Outage of POS and web payment in Retail store cluster; needs InfoSec attention	\N	\N	2025-10-02 22:43:47.413614+00	2025-10-02 22:43:47.413614+00	2	2	2	5	1	1	7	\N	\N	\N	\N	\N	2025-10-07 22:43:47.413614+00	\N	\N	\N	\N	50000.00	0.00	\N	USD	f	\N
3	Credit Card Fraud	Multiple suspicious transactions observed on several cards; preliminary ticket	\N	\N	2025-09-23 22:43:47.414504+00	2025-09-23 22:43:47.414504+00	2	2	2	2	1	1	7	\N	\N	\N	\N	\N	2025-09-28 22:43:47.414504+00	\N	\N	\N	\N	25000.00	0.00	\N	USD	f	\N
4	Reconciliation Error	Daily reconciliation mismatch: suspected human error	\N	\N	2025-09-30 22:43:47.415151+00	2025-09-30 22:43:47.415151+00	3	3	\N	\N	\N	2	8	2	\N	\N	\N	\N	2025-10-05 22:43:47.415151+00	\N	\N	\N	\N	0.00	0.00	\N	USD	f	\N
\.


--
-- Data for Name: loss_causes; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.loss_causes (id, name, description) FROM stdin;
1	System Failure	Unexpected outage of systems
2	Human Error	Error by staff/third party in process
3	External Fraud	Third-party fraud (card, payment, social engineering)
4	Regulatory Breach	Breach resulting in regulatory fine
\.


--
-- Data for Name: incident_cause; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_cause (incident_id, loss_cause_id) FROM stdin;
3	3
\.


--
-- Data for Name: measure_status_ref; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.measure_status_ref (id, code, name) FROM stdin;
1	OPEN	Open
2	IN_PROGRESS	In Progress
3	DONE	Done
4	OVERDUE	Overdue
5	CANCELLED	Cancelled
\.


--
-- Data for Name: measures; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.measures (id, description, responsible_id, deadline, status_id, created_at, created_by, updated_at, closed_at, closure_comment) FROM stdin;
1	Block suspicious card numbers	5	2025-10-11	1	2025-10-04 22:43:47.416431+00	7	\N	\N	\N
2	Patch core server	9	2025-10-18	2	2025-10-04 22:43:47.416431+00	9	\N	\N	\N
\.


--
-- Data for Name: incident_measure; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_measure (incident_id, measure_id) FROM stdin;
3	1
\.


--
-- Data for Name: incident_required_fields; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_required_fields (status_id, field_name, required) FROM stdin;
1	title	t
1	description	t
1	business_unit_id	f
1	near_miss	f
1	gross_loss_amount	f
2	business_process_id	t
2	product_id	f
2	gross_loss_amount	f
3	gross_loss_amount	t
3	recovery_amount	f
3	net_loss_amount	t
3	currency_code	t
3	basel_event_type_id	t
4	gross_loss_amount	t
4	net_loss_amount	t
4	currency_code	t
4	basel_event_type_id	t
5	gross_loss_amount	t
5	net_loss_amount	t
5	currency_code	t
5	basel_event_type_id	t
\.


--
-- Data for Name: risk_categories; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.risk_categories (id, name, description) FROM stdin;
1	Operational Risk	Operational risk general
2	IT Risk	Risks related to IT and systems
3	Fraud Risk	Fraud risk
4	Compliance Risk	Regulatory and compliance risk
\.


--
-- Data for Name: risks; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.risks (id, description, risk_category_id, basel_event_type_id, business_unit_id, business_process_id, product_id, inherent_likelihood, inherent_impact, residual_likelihood, residual_impact, created_by, created_at, updated_at) FROM stdin;
1	Core banking disruption from major outage	2	5	5	5	\N	4	5	3	3	9	2025-10-04 22:43:47.409191+00	\N
2	Retail card fraud spike	3	2	2	2	2	5	4	3	3	7	2025-10-04 22:43:47.409191+00	\N
\.


--
-- Data for Name: incident_risk; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_risk (incident_id, risk_id) FROM stdin;
2	1
\.


--
-- Data for Name: incident_routing_rules; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.incident_routing_rules (id, route_to_role_id, route_to_bu_id, predicate, priority, description, active) FROM stdin;
1	\N	8	{"min_amount": 1000000}	5	Material losses > $1M -> Group ORM BU	t
2	5	7	{"business_unit_id": 2, "basel_event_type_id": 5}	10	IT/security events in Retail -> InfoSec	t
3	6	6	{"basel_event_type_id": 2}	15	External fraud -> Fraud Investigation Unit	t
\.


--
-- Data for Name: key_risk_indicators; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.key_risk_indicators (id, name, definition, unit, threshold_green, threshold_amber, threshold_red, frequency, responsible_id, risk_id, created_at, updated_at, active) FROM stdin;
1	System Downtime Hours	Total hours of downtime per month	hours	2	5	10	Monthly	9	1	2025-10-04 22:43:47.417961+00	\N	t
2	Ops Staff Turnover %	Monthly turnover % in Ops	%	5	10	20	Monthly	8	\N	2025-10-04 22:43:47.417961+00	\N	t
\.


--
-- Data for Name: kri_measurements; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.kri_measurements (id, kri_id, period_start, period_end, value, threshold_status, comment, recorded_at, recorded_by) FROM stdin;
1	1	2025-08-01	2025-08-31	6	Amber	\N	2025-10-04 22:43:47.418744+00	9
2	2	2025-08-01	2025-08-31	12	Red	\N	2025-10-04 22:43:47.418744+00	8
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.notifications (id, entity_type, entity_id, event_type, sla_stage, recipient_id, recipient_role_id, routing_rule_id, triggered_by, created_at, due_at, method, payload, status, attempts, last_error, sent_at, active) FROM stdin;
\.


--
-- Data for Name: risk_category_event_type; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.risk_category_event_type (risk_category_id, basel_event_type_id) FROM stdin;
3	2
3	1
2	5
1	6
\.


--
-- Data for Name: risk_control; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.risk_control (risk_id, control_id) FROM stdin;
\.


--
-- Data for Name: risk_measure; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.risk_measure (risk_id, measure_id) FROM stdin;
\.


--
-- Data for Name: simplified_event_types_ref; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.simplified_event_types_ref (id, name, short_desc, front_end_hint, is_active) FROM stdin;
\.


--
-- Data for Name: simplified_to_basel_event_map; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.simplified_to_basel_event_map (id, simplified_id, basel_id, is_default) FROM stdin;
\.


--
-- Data for Name: sla_config; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.sla_config (key, value_int, updated_at) FROM stdin;
draft_days	5	2025-10-04 22:43:47.400454+00
review_days	3	2025-10-04 22:43:47.400454+00
validation_days	7	2025-10-04 22:43:47.400454+00
\.


--
-- Data for Name: user_notifications; Type: TABLE DATA; Schema: public; Owner: devuser
--

COPY public.user_notifications (id, notification_id, user_id, is_read, created_at, read_at) FROM stdin;
\.


--
-- Name: basel_business_lines_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.basel_business_lines_id_seq', 7, true);


--
-- Name: basel_event_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.basel_event_types_id_seq', 7, true);


--
-- Name: business_processes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.business_processes_id_seq', 7, true);


--
-- Name: business_units_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.business_units_id_seq', 9, true);


--
-- Name: controls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.controls_id_seq', 2, true);


--
-- Name: incident_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.incident_audit_id_seq', 4, true);


--
-- Name: incident_routing_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.incident_routing_rules_id_seq', 3, true);


--
-- Name: incident_status_ref_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.incident_status_ref_id_seq', 5, true);


--
-- Name: incidents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.incidents_id_seq', 4, true);


--
-- Name: key_risk_indicators_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.key_risk_indicators_id_seq', 2, true);


--
-- Name: kri_measurements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.kri_measurements_id_seq', 2, true);


--
-- Name: loss_causes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.loss_causes_id_seq', 4, true);


--
-- Name: measure_status_ref_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.measure_status_ref_id_seq', 5, true);


--
-- Name: measures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.measures_id_seq', 2, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.products_id_seq', 3, true);


--
-- Name: risk_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.risk_categories_id_seq', 4, true);


--
-- Name: risks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.risks_id_seq', 2, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.roles_id_seq', 8, true);


--
-- Name: simplified_event_types_ref_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.simplified_event_types_ref_id_seq', 1, false);


--
-- Name: simplified_to_basel_event_map_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.simplified_to_basel_event_map_id_seq', 1, false);


--
-- Name: user_notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.user_notifications_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devuser
--

SELECT pg_catalog.setval('public.users_id_seq', 9, true);


--
-- PostgreSQL database dump complete
--

\unrestrict kzWqRDxLwRKbs0YYf4Z5M9Xfb6gvYaOLbgak3WOjkdMxOlWw4rcXMWduILlhs8h

