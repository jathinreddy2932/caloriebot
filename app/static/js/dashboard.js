// CalorieBot Dashboard Logic & Charts
let categoryChart = null;
let historyChart = null;

document.addEventListener("DOMContentLoaded", () => {
    initCategoryChart();
    loadHistoryChart();
    setupQuickLogForm();
});

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
                    "#f59e0b", // Amber (Breakfast)
                    "#3b82f6", // Blue (Lunch)
                    "#a855f7", // Purple (Snacks)
                    "#6366f1", // Indigo (Dinner)
                    "#ec4899"  // Pink (Meanwhile)
                ],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#94a3b8",
                        font: { size: 11, family: "sans-serif" },
                        boxWidth: 12,
                        padding: 15
                    }
                }
            },
            cutout: "68%"
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
                        backgroundColor: calories.map(c => c > dailyBudget ? "#f43f5e" : "#10b981"),
                        borderRadius: 6,
                        barPercentage: 0.6
                    },
                    {
                        type: "line",
                        label: "Target Budget (1750 kcal)",
                        data: budgets,
                        borderColor: "#64748b",
                        borderWidth: 2,
                        borderDash: [5, 5],
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
                        ticks: { color: "#64748b", font: { size: 11 } }
                    },
                    y: {
                        grid: { color: "#1e293b" },
                        ticks: { color: "#64748b", font: { size: 11 } },
                        suggestedMax: 2200,
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#94a3b8",
                            font: { size: 11 },
                            boxWidth: 12,
                            padding: 15
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error("Error loading history chart:", err);
    }
}

function setupQuickLogForm() {
    const form = document.getElementById("quickLogForm");
    const input = document.getElementById("mealInput");
    const btn = document.getElementById("logBtn");
    const feedback = document.getElementById("logFeedback");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        btn.disabled = true;
        btn.innerHTML = `<span>⏳ Analyzing with Gemini...</span>`;
        feedback.className = "hidden";

        try {
            const res = await fetch("/api/meals", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });

            if (!res.ok) throw new Error("Failed to log meal");

            const data = await res.json();
            feedback.className = "mt-3 p-3 rounded-lg text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
            feedback.innerHTML = `✅ <b>${data.meal.meal_type.toUpperCase()} Logged:</b> ${data.meal.total_calories} kcal (P: ${data.meal.total_protein}g). ${data.tip ? '<i>' + data.tip + '</i>' : ''}`;

            input.value = "";
            setTimeout(() => {
                window.location.reload();
            }, 1200);
        } catch (err) {
            feedback.className = "mt-3 p-3 rounded-lg text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30";
            feedback.textContent = `⚠️ Error: ${err.message}`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>⚡ Log Meal</span>`;
        }
    });
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
