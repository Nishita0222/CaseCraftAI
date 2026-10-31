import React, { useEffect, useState } from "react";

import {
    FileText,
    Download,
    ShieldCheck,
    Users,
    BriefcaseBusiness,
    RefreshCw
} from "lucide-react";

import {
    getCaseStudy,
    exportWord,
    downloadWord
} from "./api";


function App() {

    const [caseStudy, setCaseStudy] = useState(null);

    const [loading, setLoading] = useState(false);

    const [selected, setSelected] = useState("");

    const [message, setMessage] = useState("");

    const audiences = [

        {
            id: "gatekeeper",
            title: "Gatekeeper Version",
            description:
                "Security, compliance and deployment details",
            icon: ShieldCheck
        },

        {
            id: "user",
            title: "User Version",
            description:
                "Implementation, workflow and team experience",
            icon: Users
        },

        {
            id: "buyer",
            title: "Buyer Version",
            description:
                "Business results, verified KPIs and ROI",
            icon: BriefcaseBusiness
        }

    ];


    useEffect(() => {

        loadCaseStudy();

    }, []);


    const loadCaseStudy = async () => {

        try {

            const data = await getCaseStudy();

            setCaseStudy(data);

        } catch (error) {

            setMessage("Unable to load case study.");

        }

    };


    const handleExport = async (audience) => {

        try {

            setLoading(true);

            setSelected(audience);

            setMessage("Generating Word document...");

            const result = await exportWord(audience);

            await downloadWord(result.filename);

            setMessage(
                `${audience} Word document downloaded successfully!`
            );

        } catch (error) {

            setMessage(
                error.response?.data?.detail ||
                "Something went wrong while exporting."
            );

        } finally {

            setLoading(false);

            setSelected("");

        }

    };


    if (!caseStudy) {

        return (
            <div className="loading">
                Loading Project Drishti...
            </div>
        );

    }


    return (

        <div className="app">

            <header className="header">

                <div className="brand">

                    <div className="logo">
                        <FileText size={25} />
                    </div>

                    <div>
                        <h2>Project Drishti</h2>
                        <p>AI Case Study Generation System</p>
                    </div>

                </div>

                <span className="status">
                    Draft Generated
                </span>

            </header>


            <main className="container">

                <section className="hero">

                    <p className="eyebrow">
                        CASE STUDY EXPORT CENTER
                    </p>

                    <h1>
                        Generate Your Case Study
                    </h1>

                    <p>
                        Convert your AI-generated project insights
                        into professional Word documents.
                    </p>

                </section>


                <section className="project-card">

                    <div>

                        <span className="small-label">
                            CURRENT PROJECT
                        </span>

                        <h2>Project Drishti</h2>

                        <p>
                            AI-Powered Safety Camera & Gate Analytics
                        </p>

                    </div>

                    <div className="project-info">

                        <div>
                            <span>Project Period</span>
                            <strong>Jan – Sep 2026</strong>
                        </div>

                        <div>
                            <span>Approval Status</span>
                            <strong className="pending">
                                Pending
                            </strong>
                        </div>

                    </div>

                </section>


                <section className="export-section">

                    <div className="section-heading">

                        <div>
                            <h2>Choose your audience</h2>

                            <p>
                                Generate a version suited to each reader.
                            </p>
                        </div>

                    </div>


                    <div className="cards">

                        {audiences.map((item) => {

                            const Icon = item.icon;

                            return (

                                <div
                                    className="audience-card"
                                    key={item.id}
                                >

                                    <div className="card-icon">
                                        <Icon size={25} />
                                    </div>

                                    <h3>{item.title}</h3>

                                    <p>{item.description}</p>

                                    <button
                                        onClick={() =>
                                            handleExport(item.id)
                                        }
                                        disabled={loading}
                                    >

                                        {loading &&
                                        selected === item.id ? (

                                            <>
                                                <RefreshCw
                                                    size={16}
                                                    className="spin"
                                                />
                                                Generating...
                                            </>

                                        ) : (

                                            <>
                                                <Download size={17} />
                                                Export Word
                                            </>

                                        )}

                                    </button>

                                </div>

                            );

                        })}

                    </div>

                </section>


                {message && (

                    <div className="message">
                        {message}
                    </div>

                )}


                <section className="preview">

                    <h2>Case Study Preview</h2>

                    <h3>Executive Summary</h3>

                    <p>
                        {caseStudy.executive_summary}
                    </p>

                    <h3>Business Challenge</h3>

                    <p>
                        {caseStudy.business_challenge}
                    </p>

                    <h3>Solution Implemented</h3>

                    <p>
                        {caseStudy.solution}
                    </p>

                </section>


                <div className="notice">

                    <ShieldCheck size={21} />

                    <div>

                        <strong>Human approval required</strong>

                        <p>
                            Downloaded Word documents are drafts for
                            review. External publication remains blocked
                            until authorised human approval is received.
                        </p>

                    </div>

                </div>

            </main>

        </div>

    );

}

export default App;