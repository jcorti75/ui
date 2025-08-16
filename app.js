async function submitRecommendation() {
    const top = document.getElementById("top").files[0];
    const bottom = document.getElementById("bottom").files[0];
    const shoes = document.getElementById("shoes").files;
  
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
  
    const response = await fetch("https://your-backend.fly.dev/recommend", {
      method: "POST",
      body: formData,
    });
  
    const data = await response.json();
    console.log(data);
    document.getElementById("results").innerHTML = `
      <h3>✅ Mejor opción: Zapato #${data.best_index + 1}</h3>
      <pre>${JSON.stringify(data.results, null, 2)}</pre>
    `;
  }
  