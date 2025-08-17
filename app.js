async function submitRecommendation() {
  console.log("🚀 Iniciando recomendación...");
  
  const top = document.getElementById("top").files[0];
  const bottom = document.getElementById("bottom").files[0];
  const shoes = document.getElementById("shoes").files;
  
  console.log("📁 Archivos:", { top, bottom, shoes: shoes.length });
  
  if (!top || !bottom || shoes.length === 0) {
    alert("Debes subir todas las prendas.");
    return;
  }
  
  const formData = new FormData();
  formData.append("top", top);
  formData.append("bottom", bottom);
  for (let i = 0; i < shoes.length; i++) {
    formData.append("shoes", shoes[i]);
  }
  
  console.log("📤 Enviando request a API...");
  
  try {
    const response = await fetch("https://outfit-recommender.fly.dev/recommend", {
      method: "POST",
      body: formData,
    });
    
    console.log("📥 Response status:", response.status);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log("✅ Data recibida:", data);
    
    document.getElementById("results").innerHTML = `
      <h3>✅ Mejor opción: Zapato #${data.best_index + 1}</h3>
      <pre>${JSON.stringify(data.results, null, 2)}</pre>
    `;
  } catch (error) {
    console.error("❌ Error:", error);
    document.getElementById("results").innerHTML = `
      <h3>❌ Error: ${error.message}</h3>
    `;
  }
}
  