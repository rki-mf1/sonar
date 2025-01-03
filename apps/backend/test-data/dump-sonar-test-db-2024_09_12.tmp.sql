--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3
-- Dumped by pg_dump version 16.2 (Ubuntu 16.2-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;



--
-- Data for Name: file_processing; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.file_processing (id, file_name, processing_job_id) FROM stdin;
1	2024-07-12_12-44-32.322.d968e9.zip	1
2	2024-07-12_12-44-32.549.388219.zip	1
3	2024-09-12_09-04-23.415.b87c3e.zip	7
4	2024-09-12_09-04-23.582.cli_prop_987a7efb-a5d6-4ced-80ac-4edc7865c1a1.zip	8
5	2024-09-12_09-04-23.876.cli_prop_6b45f3a3-99c6-4c38-892b-77b544c455d1.zip	9
6	2024-09-12_09-04-24.158.cli_prop_2efe0cf7-e508-4b84-be71-ce1963ee2d86.zip	10
\.


--
-- Data for Name: import_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.import_log (id, type, file_id, updated, success, exception_text, stack_trace) FROM stdin;
\.


--
-- Data for Name: lineage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.lineage (id, name, parent_id) FROM stdin;
4270	B	\N
4271	BA.1	\N
4272	BA.1.1	\N
4273	BA.1.17	\N
4274	B.1.617	\N
4275	BA.5	\N
4276	BA.5.2	\N
4277	BA.2	\N
4278	BA.5.3	\N
4279	AY.4	\N
4280	B.1.617.2	\N
4281	B.1	4270
4282	BA.1	4270
4283	BA.5	4270
4284	BA.2	4270
4285	BA.1.1	4271
4286	BC.1	4271
4287	BC.2	4271
4288	BA.1.2	4271
4289	BA.1.3	4271
4290	BA.1.4	4271
4291	BA.1.5	4271
4292	BA.1.6	4271
4293	BA.1.7	4271
4294	BA.1.8	4271
4295	BA.1.9	4271
4296	BA.1.10	4271
4297	BA.1.12	4271
4298	BA.1.13	4271
4299	BA.1.13.1	4271
4300	BA.1.14	4271
4301	BA.1.14.1	4271
4302	BA.1.14.2	4271
4303	BA.1.15	4271
4304	BA.1.16	4271
4305	BA.1.17	4271
4306	BD.1	4271
4307	BA.1.18	4271
4308	BA.1.19	4271
4309	BA.1.20	4271
4310	BA.1.21	4271
4311	BA.1.22	4271
4312	BA.1.23	4271
4313	BA.1.24	4271
4314	B.1.617	4271
4315	BA.1.1.1	4272
4316	BA.1.1.2	4272
4317	BA.1.1.3	4272
4318	BA.1.1.4	4272
4319	BA.1.1.5	4272
4320	BA.1.1.6	4272
4321	BA.1.1.7	4272
4322	BA.1.1.8	4272
4323	BA.1.1.9	4272
4324	BA.1.17.1	4273
4325	BA.1.17.2	4273
4326	B.1.617.2	4274
4327	BA.5.2	4275
4328	BF.2	4275
4329	BA.5.3	4275
4330	BA.5.2.1	4276
4331	BA.5.2.6	4276
4332	BA.2.36	4277
4333	BA.2.9	4277
4334	BA.5.3.1	4278
4335	AY.4.1	4279
4336	AY.4.2	4279
4337	AY.4.3	4279
4338	AY.4.4	4279
4339	AY.4.5	4279
4340	AY.4.6	4279
4341	AY.4.7	4279
4342	AY.4.8	4279
4343	AY.4.9	4279
4344	AY.4.10	4279
4345	AY.4.11	4279
4346	AY.4.12	4279
4347	AY.4.13	4279
4348	AY.4.14	4279
4349	AY.4.15	4279
4350	AY.4.16	4279
4351	AY.4.17	4279
4352	AY.4	4280
4353	AY.98	4280
\.


--
-- Data for Name: processing_job; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.processing_job (id, job_name, status, entry_time) FROM stdin;
1	cli_55199e67-4998-41a0-b105-10772fa1c626	Q	2024-07-12 12:44:32.337657+00
6	cli_queue-job	Q	2024-07-12 15:44:32.337+00
2	cli_fail-job	F	2024-07-12 13:44:32.337+00
7	cli_b25fc337-58bc-4c6c-8ca0-9baaf3abfc70	Q	2024-09-12 09:04:23.434519+00
8	cli_prop_987a7efb-a5d6-4ced-80ac-4edc7865c1a1	Q	2024-09-12 09:04:23.603084+00
9	cli_prop_6b45f3a3-99c6-4c38-892b-77b544c455d1	Q	2024-09-12 09:04:23.897942+00
10	cli_prop_2efe0cf7-e508-4b84-be71-ce1963ee2d86	Q	2024-09-12 09:04:24.183684+00
\.


--
-- Data for Name: property; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.property (id, name, datatype, querytype, description, target, standard) FROM stdin;
1	sequencing_reason	value_varchar	\N	\N	\N	\N
2	sample_type	value_varchar	\N	\N	\N	\N
267	euro	value_float	\N	\N	\N	\N
269	comments	value_text	\N	\N	\N	\N
274	age	value_integer	\N	\N	\N	\N
\.


--
-- Data for Name: sample; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sample (id, name, datahash, sequence_id, collection_date, country, genome_completeness, host, lab, length, lineage, sequencing_tech, zip_code, init_upload_date, last_update_date) FROM stdin;
1	IMS-10338-CVDP-BAF51380-B921-4701-98ED-8DAACF2C7D11	\N	1	2021-12-30	USA	complete	\N	DEMIS-SL-10338	\N	AY.4	ILLUMINA	60327	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
2	IMS-10150-CVDP-469B04EB-4D49-4109-9F81-0531CE275F6D	\N	2	2022-03-07	UK	partial	\N	DEMIS-SL-10150	\N	BA.1.1	ILLUMINA	92637	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
3	IMS-10280-CVDP-2A9F0F09-E708-4CB2-91E4-9CD5F68C9093	\N	3	2022-06-10	Germany	partial	\N	DEMIS-SL-10280	\N	BA.2.36	ILLUMINA	16816	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
4	IMS-10150-CVDP-C81AA5B8-AAF9-41C9-B64D-1EEBF0E9A01A	\N	4	2022-01-11	UK	complete	\N	DEMIS-SL-10150	\N	BA.1.17.2	ILLUMINA	51375	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
5	IMS-10150-CVDP-E3D797D9-FF1A-4BE8-AE50-13E30B77E18A	\N	5	2022-03-09	Thailand	partial	\N	DEMIS-SL-10150	\N	BA.2.9	ILLUMINA	92637	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
6	IMS-10768-CVDP-0E69A26F-7AC0-4631-B0F3-192FF005FDA0	\N	6	2023-01-18	Japan	complete	\N		\N	BA.5.2.6	ILLUMINA	65451	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
7	IMS-10023-CVDP-0E428B50-D29B-4173-97B4-D7575296CD84	\N	7	2022-01-13	USA	partial	\N	DEMIS-SL-10023	\N	BA.1	ILLUMINA	09221	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
8	IMS-10259-CVDP-3A88C5D5-D88B-458A-9040-843D8CBCEA2D	\N	8	2022-05-17	Korea	partial	\N	DEMIS-SL-10259	\N	BA.2	ILLUMINA	45147	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
9	IMS-10150-CVDP-6EC46FD8-1FBA-427D-A559-411BCF94B679	\N	9	2021-12-30	Germany	complete	\N	DEMIS-SL-10150	\N	AY.98	ILLUMINA	70771	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
10	IMS-10116-CVDP-77AB96B7-B9FB-46D6-B844-F9356151F2CA	\N	10	2022-01-30	France	partial	\N	DEMIS-SL-10116	\N	BA.1.1	ILLUMINA	69126	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
11	IMS-10013-CVDP-7629957A-D507-442D-BD2A-18236F7DB38C	\N	11	2022-06-18	UK	partial	\N	DEMIS-SL-10013	\N	BA.5.3.1	ILLUMINA	04779	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
12	IMS-10013-CVDP-A38AD576-D6B0-4585-9D11-38C4BAFE862D	\N	12	2022-09-26	USA	complete	\N	DEMIS-SL-10013	\N	BA.5.2	ILLUMINA	44799	2024-07-12 12:38:03.392997+00	2024-07-12 13:38:03.392+00
\.


--
-- Data for Name: sample2property; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sample2property (id, value_integer, value_float, value_text, value_varchar, value_blob, value_date, value_zip, property_id, sample_id) FROM stdin;
1	\N	\N	\N	X	\N	\N	\N	1	1
2	\N	\N	\N	X	\N	\N	\N	2	1
51	\N	63.33	\N	\N	\N	\N	\N	267	1
88	48	\N	\N	\N	\N	\N	\N	274	1
89	\N	\N	The legend of the haunted vending machine: A spooky tale of ghostly snacks, possessed buttons, and a craving for revenge.	\N	\N	\N	\N	269	1
3	\N	\N	\N	X	\N	\N	\N	1	2
4	\N	\N	\N	X	\N	\N	\N	2	2
54	\N	31.16	\N	\N	\N	\N	\N	267	2
93	18	\N	\N	\N	\N	\N	\N	274	2
94	\N	\N	The curious case of the disappearing socks: A tale of mismatched mysteries and runaway laundry.	\N	\N	\N	\N	269	2
5	\N	\N	\N	N	\N	\N	\N	1	3
6	\N	\N	\N	S002	\N	\N	\N	2	3
57	\N	66.11	\N	\N	\N	\N	\N	267	3
98	84	\N	\N	\N	\N	\N	\N	274	3
99	\N	\N	The misadventures of Professor Forgetful: A forgettable tale of absent-minded antics and misplaced memories.	\N	\N	\N	\N	269	3
7	\N	\N	\N	X	\N	\N	\N	1	4
8	\N	\N	\N	S002	\N	\N	\N	2	4
60	\N	19.91	\N	\N	\N	\N	\N	267	4
103	91	\N	\N	\N	\N	\N	\N	274	4
104	\N	\N	The curious case of the disappearing socks: A tale of mismatched mysteries and runaway laundry.	\N	\N	\N	\N	269	4
9	\N	\N	\N	X	\N	\N	\N	1	5
10	\N	\N	\N	S002	\N	\N	\N	2	5
63	\N	2.47	\N	\N	\N	\N	\N	267	5
108	16	\N	\N	\N	\N	\N	\N	274	5
109	\N	\N	The secret life of office plants: A documentary on the dramatic world of potted flora and their water cooler gossip.	\N	\N	\N	\N	269	5
11	\N	\N	\N	N	\N	\N	\N	1	6
12	\N	\N	\N	S002	\N	\N	\N	2	6
66	\N	1.47	\N	\N	\N	\N	\N	267	6
113	90	\N	\N	\N	\N	\N	\N	274	6
114	\N	\N	The culinary catastrophe: A kitchen comedy of errors featuring burnt toast, exploded souffl�s, and a rogue blender.	\N	\N	\N	\N	269	6
13	\N	\N	\N	N	\N	\N	\N	1	7
14	\N	\N	\N	S001	\N	\N	\N	2	7
69	\N	39.95	\N	\N	\N	\N	\N	267	7
118	52	\N	\N	\N	\N	\N	\N	274	7
119	\N	\N	The curious case of the disappearing dessert: A culinary mystery involving vanished cakes, stolen cookies, and a trail of crumbs leading to a sweet tooth culprit.	\N	\N	\N	\N	269	7
15	\N	\N	\N	N	\N	\N	\N	1	8
16	\N	\N	\N	S008	\N	\N	\N	2	8
72	\N	63.09	\N	\N	\N	\N	\N	267	8
123	99	\N	\N	\N	\N	\N	\N	274	8
124	\N	\N	The culinary catastrophe: A kitchen comedy of errors featuring burnt toast, exploded souffl�s, and a rogue blender.	\N	\N	\N	\N	269	8
17	\N	\N	\N	X	\N	\N	\N	1	9
18	\N	\N	\N	S002	\N	\N	\N	2	9
75	\N	91.46	\N	\N	\N	\N	\N	267	9
128	66	\N	\N	\N	\N	\N	\N	274	9
129	\N	\N	The sound of thunder rumbled ominously in the distance, as dark clouds gathered overhead. A storm was brewing, casting an air of anticipation over the sleepy town.	\N	\N	\N	\N	269	9
19	\N	\N	\N	N	\N	\N	\N	1	10
20	\N	\N	\N	X	\N	\N	\N	2	10
78	\N	26.93	\N	\N	\N	\N	\N	267	10
133	79	\N	\N	\N	\N	\N	\N	274	10
134	\N	\N	The laughter of children echoed through the playground, mingling with the sound of birdsong in the trees. It was a scene of pure joy and innocence, a reminder of the simple pleasures in life.	\N	\N	\N	\N	269	10
21	\N	\N	\N	N	\N	\N	\N	1	11
22	\N	\N	\N	S001	\N	\N	\N	2	11
81	\N	42.64	\N	\N	\N	\N	\N	267	11
138	83	\N	\N	\N	\N	\N	\N	274	11
139	\N	\N	The epic battle of the sibling rivalry: A family feud featuring sibling showdowns, petty squabbles, and the quest for parental attention.	\N	\N	\N	\N	269	11
23	\N	\N	\N	N	\N	\N	\N	1	12
24	\N	\N	\N	S001	\N	\N	\N	2	12
84	\N	73.17	\N	\N	\N	\N	\N	267	12
143	84	\N	\N	\N	\N	\N	\N	274	12
144	\N	\N	\N	\N	\N	\N	\N	269	12
\.


--
-- Data for Name: sequence; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sequence (id, seqhash) FROM stdin;
1	09b05391ed038a810f767e007b74bd5edb194508648b30a1fdce639474334365
2	d7adf70cb6b07449ffe8e204f9b16827da3a910bf1dccd328b6cea0656868d21
3	096c8366c9b1707603aa80e97d30d5e12bbac4f4f3135a7117dd8fc2c6ce7412
4	38a733cce2808b474c22ab4f36c53a701d3159c1b02207bf90fdd7767ce65faa
5	dbff03a2fd359e7432785d96be7a9bce6c6e860d3165d2bbb82daa7aaaf4095f
6	51f1c4bfa1632fe6f5ee2c926bbc5597a55b657ecbf9d822f1e8b2e004c496e5
7	969d9df12e15e943c929a0b950b35b4de9ffcb4c00f35f637fb0dcd44c5ce017
8	07ec797792fe36854b13eff45da15002d1286c91dfbceffd3482767d82fdb6a1
9	9774da801f2026c33ac1f689907a6a20b9af9ddfa71a579826fa59dc89ace51b
10	d6d1b96148bfd60c68a181746e7865b8712f33f944fb7827c5ccfee8ab784646
11	3c02255278ac729c0717621eb028cbd1d6db8fad2e9f9958a537d5a9fc61db37
12	4a9b9a95ef99fefcdcad331f89fc4b005f431f5162afc953049f21381ed19d7e
\.


--
-- PostgreSQL database dump complete
--

