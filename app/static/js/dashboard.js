// CareAscendium Style Dashboard Logic
let categoryChart = null;
let historyChart = null;

document.addEventListener("DOMContentLoaded", () => {
    initCategoryChart();
    loadHistoryChart();
    setupUnifiedForm();
    setupWeightForm();
});

// Tab Navigation Switcher
function switchTab(tabName) {
    const tabs = ['today', 'history', 'weight'];
    tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        const btn = document.getElementById(`tabBtn-${t}`);
        if (t === tabName) {
            el.classList.remove('hidden');
            btn.className = "py-3 border-b-2 border-[#63a821] text-[#0d2a5c] font-bold flex items-center gap-2";
        } else {
            el.classList.add('hidden');
            btn.className = "py-3 border-b-2 border-transparent text-slate-500 hover:text-[#0d2a5c] flex items-center gap-2 font-medium";
        }
    });
}

function initCategoryChart() {
    const ctx = document.getElementById("mealCategoryChart");
    if (!ctx) return;

    const dataValues = [
        initialCategoryData.breakfast || 0,
        initialCategoryData.lunch || 0,
        initialCategoryData.snack || 0,
        initialCategoryData.dinner || 0,
        initialCategoryData.meanwhile || 0
    ];

    categoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Breakfast", "Lunch", "Snacks", "Dinner", "Meanwhile"],
            datasets: [{
                data: dataValues,
                backgroundColor: [
                    "#f59e0b", // Amber
                    "#0d2a5c", // Deep Navy
                    "#63a821", // CareAscendium Green
                    "#153c7f", // Royal Blue
                    "#ec4899"  // Pink
                ],
                borderWidth: 2,
                borderColor: "#ffffff",
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#64748b",
                        font: { size: 11, family: "Poppins" },
                        boxWidth: 10,
                        padding: 12
                    }
                }
            },
            cutout: "70%"
        }
    });
}

async function loadHistoryChart() {
    const ctx = document.getElementById("historyChart");
    if (!ctx) return;

    try {
        const res = await fetch("/api/history?days=7");
        const data = await res.json();

        const labels = data.map(d => d.date);
        const calories = data.map(d => d.calories);
        const budgets = data.map(d => d.budget);

        historyChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Consumed (kcal)",
                        data: calories,
                        backgroundColor: calories.map(c => c > dailyBudget ? "#ef4444" : "#63a821"),
                        borderRadius: 4,
                        barPercentage: 0.55
                    },
                    {
                        type: "line",
                        label: `Budget (${dailyBudget} kcal)`,
                        data: budgets,
                        borderColor: "#0d2a5c",
                        borderWidth: 2,
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#64748b", font: { size: 10, family: "Poppins" } }
                    },
                    y: {
                        grid: { color: "#f1f5f9" },
                        ticks: { color: "#64748b", font: { size: 10, family: "Poppins" } },
                        suggestedMax: 2200,
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#64748b",
                            font: { size: 11, family: "Poppins" },
                            boxWidth: 10,
                            padding: 12
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error("Error loading history chart:", err);
    }
}

// Unified input form handles both food logging AND weight entry!
function setupUnifiedForm() {
    const form = document.getElementById("unifiedLogForm");
    const input = document.getElementById("unifiedInput");
    const btn = document.getElementById("unifiedBtn");
    const feedback = document.getElementById("unifiedFeedback");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        btn.disabled = true;
        btn.textContent = "Processing...";
        feedback.className = "hidden";

        // Check if text is weight entry (e.g. "87kg", "87.5", "weight 86.8")
        const weightMatch = text.match(/^(?:(?:my\s+)?weight|weighed|today\s+weight)?\s*:?\s*(\d{2,3}(?:\.\d{1,2})?)\s*(?:kg|kgs|kilos?)?$/i);
        
        try {
            if (weightMatch && parseFloat(weightMatch[1]) >= 40 && parseFloat(weightMatch[1]) <= 250) {
                // Log weight
                const val = parseFloat(weightMatch[1]);
                const res = await fetch("/api/weight", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ weight_kg: val })
                });
                if (!res.ok) throw new Error("Failed to log weight");
                const data = await res.json();
                feedback.className = "mt-3 p-3 rounded-md text-xs bg-emerald-50 text-[#166534] border border-emerald-200";
                feedback.innerHTML = `✔ <b>Weight Updated:</b> ${data.weight} kg. Budget dynamically recalculated to <b>${data.stats.budget} kcal/day</b>!`;
            } else {
                // Log meal
                const res = await fetch("/api/meals", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text })
                });
                if (!res.ok) throw new Error("Failed to log meal");
                const data = await res.json();
                feedback.className = "mt-3 p-3 rounded-md text-xs bg-emerald-50 text-[#166534] border border-emerald-200";
                feedback.innerHTML = `✔ <b>${data.meal.meal_type.toUpperCase()} Logged:</b> ${data.meal.total_calories} kcal (P: ${data.meal.total_protein}g | C: ${data.meal.total_carbs}g). ${data.tip ? '<i>' + data.tip + '</i>' : ''}`;
            }

            input.value = "";
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } catch (err) {
            feedback.className = "mt-3 p-3 rounded-md text-xs bg-rose-50 text-rose-700 border border-rose-200";
            feedback.textContent = `Error: ${err.message}`;
        } finally {
            btn.disabled = false;
            btn.textContent = "Submit Entry";
        }
    });
}

function setupWeightForm() {
    const form = document.getElementById("weightLogForm");
    const input = document.getElementById("weightInputVal");
    const btn = document.getElementById("weightBtn");
    const feedback = document.getElementById("weightFeedback");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const val = parseFloat(input.value);
        if (!val || val < 40 || val > 250) {
            alert("Please enter a valid weight between 40 and 250 kg.");
            return;
        }

        btn.disabled = true;
        btn.textContent = "Saving...";

        try {
            const res = await fetch("/api/weight", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ weight_kg: val })
            });
            if (!res.ok) throw new Error("Failed to record weight");
            const data = await res.json();
            feedback.className = "mt-3 p-3 rounded-md text-xs bg-emerald-50 text-[#166534] border border-emerald-200";
            feedback.innerHTML = `✔ <b>Weight Updated to ${data.weight} kg!</b> Deficit budget: <b>${data.stats.budget} kcal</b>. Remaining to 70kg: <b>${data.stats.to_lose} kg</b>.`;

            input.value = "";
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } catch (err) {
            feedback.className = "mt-3 p-3 rounded-md text-xs bg-rose-50 text-rose-700 border border-rose-200";
            feedback.textContent = `Error: ${err.message}`;
        } finally {
            btn.disabled = false;
            btn.textContent = "Update Weight";
        }
    });
}

async function deleteWeight(weightId) {
    if (!confirm("Are you sure you want to clear this weight entry?")) return;

    try {
        const res = await fetch(`/api/weight/${weightId}`, { method: "DELETE" });
        if (res.ok) {
            window.location.reload();
        } else {
            alert("Error clearing weight entry.");
        }
    } catch (err) {
        alert("Error connecting to server.");
    }
}

async function deleteMeal(mealId) {
    if (!confirm("Are you sure you want to delete this meal entry?")) return;

    try {
        const res = await fetch(`/api/meals/${mealId}`, { method: "DELETE" });
        if (res.ok) {
            window.location.reload();
        } else {
            alert("Error deleting meal.");
        }
    } catch (err) {
        alert("Error connecting to server.");
    }
}
