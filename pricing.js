const $ = (id) => document.getElementById(id);
const money = (v) => "$" + Number(v || 0).toFixed(2);
const num = (id) => Number($(id).value || 0);
const roundMoney = (value) => Math.round(Number(value || 0) * 100) / 100;
let lastSignPricingBreakdown = [];

const PRICING = {
  sign: {
    minimumCharge: 50,
    signWastePercent: 0.10,
    graphicsWastePercent: 0.10,
    extraSmallJobWastePercent: 0.05,
    sheetSqft: 32,
    sheetPricingThreshold: 0.75,
    substrateMarkup: 2.0,
    graphicsMarkup: 2.15,
    installBaseRate: 100,
    installAdvancedRate: 125,
    designRate: 25,
    designMinimum: 25,
    tripFee: 25,
    travelRate: 20,
    travelSpeedMph: 50,
    installMinimum: 50,
    substrates: {
      "None": { cost: 0, type: "none" },
      ".040": { cost: 162, type: "sheet" },
      ".080": { cost: 230, type: "sheet" },
      "3MM PVC": { cost: 48, type: "sheet" },
      "4mm CORO": { cost: 16, type: "sheet" },
      "10mm CORO": { cost: 40, type: "sheet" },
      "ACRYLIC": { cost: 95, type: "sheet" },
      "BANNER": { cost: 24, type: "sheet" },
      "OTHER": { cost: 60, type: "sheet" }
    },
    digitalSqftCost: {
      Calendar: 35 / 60,
      Premium: 72 / 60,
      Reflective: 7,
      Translucent: 8
    },
    vinylSqftCost: {
      Calendar: 3,
      Cast: 4.5,
      Reflective: 7,
      Translucent: 8
    },
    laminateSqftCost: 0.60,
    appTapeSqftCost: 0.20,
    inkSqftCost: 0.35,
    consumableSqftCost: 0.15,
    digitalItemCharge: 4,
    vinylItemCharge: 6,
    holesCharge: 3.5,
    cornersCharge: 3.5,
    velcroCharge: 12,
    tapeCharge: 10,
    grommetEach: 2.5,
    framePerLf: { "THIN WALL": 5, WELDED: 7 },
    frameLargeAreaThreshold: 8,
    frameLargeMultiplier: 1.5,
    trimPerLf: { "J TRIM": 2.5, "L TRIM": 3.5 },
    posts: { Wood: 85, Aluminum: 140, "U-Channel": 110 },
    pvcCover: 12,
    dig: { Dirt: 45, Asphalt: 95, Concrete: 135, Unknown: 75 },
    wallMount: { Cleats: 30, "14s": 20, "Deck Screws": 15, Zipits: 18, Tapcon: 20, Tape: 15, Unknown: 20 },
    bucketBase: 125,
    bucketPerFtOver20: 2,
    screwsAllowance: 10
  },
  vehicle: {
    minimumCharge: 250,
    graphicsRates: {
      printed_calendared: 14,
      printed_cast: 16,
      cut_vinyl: 12,
      reflective: 18,
      window_perf: 16
    },
    templateSetupFee: 35,
    standardDesignFee: 250,
    designRate: 25,
    installBaseRate: 100,
    installAdvancedRate: 125,
    installMinimum: 50,
    tripFee: 25,
    travelRate: 20,
    travelSpeedMph: 50,
    removalRate: 95,
    removalMinimum: 75,
    surfacePrepFee: 35,
    hardwareFee: 50
  }
};

function setNumberValue(id, value) {
  $(id).value = roundMoney(value).toFixed(2);
}

function setPriceInputsLocked(ids, locked) {
  ids.forEach((id) => {
    $(id).readOnly = locked;
    $(id).style.background = locked ? "#eef7f2" : "";
  });
}

function calcSqft() {
  const sqft = (num("width") * num("height")) / 144;
  $("sqft").value = sqft > 0 ? sqft.toFixed(2) : "0.00";
  return sqft;
}

function calcTrimLinearFt() {
  const perimeterInches = 2 * (num("width") + num("height"));
  const linearFt = perimeterInches / 12;
  $("trim_linear_ft").textContent = `(${(linearFt > 0 ? linearFt : 0).toFixed(2)} LF)`;
  return linearFt;
}

function calcTravelCharge(distance, config) {
  if (distance <= 0) return 0;
  const travelHours = distance / config.travelSpeedMph;
  return config.tripFee + (travelHours * config.travelRate);
}

function selectedOptions() {
  return Array.from(document.querySelectorAll(".opt:checked")).map((el) => {
    if (el.id === "corners_opt") return `${el.value} (${$("corners_size").value})`;
    if (el.id === "holes_opt") return `${el.value} (${$("holes_size").value})`;
    if (el.id === "grommets_opt") {
      if ($("grommets_pattern").value === "Every ___ Feet") {
        return `${el.value} (Every ${$("grommets_spacing").value || "1"} Feet)`;
      }
      return `${el.value} (${$("grommets_pattern").value})`;
    }
    if (el.id === "posts_opt") return `${el.value} (${$("posts_type").value})`;
    if (el.id === "dig_opt") return `${el.value} (${$("dig_surface").value})`;
    if (el.id === "wall_mount_opt") return `${el.value} (${$("wall_mount_type").value})`;
    if (el.id === "bucket_truck_opt") return `${el.value}${num("bucket_height") > 0 ? ` (${num("bucket_height")} ft)` : ""}`;
    if (el.classList.contains("frame-opt")) return `${el.value} FRAME`;
    return el.value;
  });
}

function selectedItems() {
  const items = [];
  const digital = num("item_digital");
  const vinyl = num("item_vinyl");
  const installInstructions = $("install_instructions").value.trim();
  const graphicsMode = $("graphics_mode").value;
  if (graphicsMode === "DIGITAL") items.push(`DIGITAL (${$("digital_type").value})`);
  if (graphicsMode === "VINYL") items.push(`VINYL (${$("vinyl_type").value})`);
  if (graphicsMode === "DIGITAL" && digital > 0) items.push(`DIGITAL ITEMS: ${digital}`);
  if (graphicsMode === "VINYL" && vinyl > 0) items.push(`VINYL ITEMS: ${vinyl}`);
  if (installInstructions) items.push(`INSTALL INSTRUCTIONS: ${installInstructions}`);
  return items;
}

function calcSignOtherCharges(perimeterLf) {
  let other = 0;
  if ($("holes_opt").checked) other += PRICING.sign.holesCharge;
  if ($("corners_opt").checked) other += PRICING.sign.cornersCharge;
  if ($("grommets_opt").checked) {
    let count = 4;
    if ($("grommets_pattern").value === "Top Corners") count = 2;
    if ($("grommets_pattern").value === "Every ___ Feet") {
      const spacing = Math.max(1, num("grommets_spacing"));
      count = Math.max(4, Math.ceil(perimeterLf / spacing));
    }
    other += count * PRICING.sign.grommetEach;
  }
  if (selectedOptions().includes("VELCRO")) other += PRICING.sign.velcroCharge;
  if (selectedOptions().includes("D/S TAPE")) other += PRICING.sign.tapeCharge;
  return other;
}

function calcSignHardwareCharges(trimLf, qty, sqftEach) {
  let hardware = 0;
  const components = [];
  if ($("frame_included").checked) {
    const frameChoice = document.querySelector('input[name="frame_choice"]:checked');
    if (frameChoice) {
      let frameCost = trimLf * (PRICING.sign.framePerLf[frameChoice.value] || 0);
      let detail = `Frame perimeter is ${trimLf.toFixed(2)} linear feet, billed at ${money(PRICING.sign.framePerLf[frameChoice.value] || 0)} per linear foot.`;
      if (sqftEach > PRICING.sign.frameLargeAreaThreshold) {
        frameCost *= PRICING.sign.frameLargeMultiplier;
        detail += ` Because the sign is over ${PRICING.sign.frameLargeAreaThreshold} sq ft, the frame rate is multiplied by ${PRICING.sign.frameLargeMultiplier.toFixed(2)}.`;
      }
      hardware += frameCost;
      components.push({ label: `${frameChoice.value} frame`, detail, amount: frameCost });
    }
  }
  if ($("trim_included").checked) {
    const trimChoice = document.querySelector('input[name="trim_choice"]:checked');
    if (trimChoice) {
      const trimCost = trimLf * (PRICING.sign.trimPerLf[trimChoice.value] || 0);
      hardware += trimCost;
      components.push({
        label: `${trimChoice.value} trim`,
        detail: `Trim perimeter is ${trimLf.toFixed(2)} linear feet, billed at ${money(PRICING.sign.trimPerLf[trimChoice.value] || 0)} per linear foot.`,
        amount: trimCost
      });
    }
  }
  if ($("posts_opt").checked) {
    const postsCost = (PRICING.sign.posts[$("posts_type").value] || 0) * qty;
    const screwsCost = PRICING.sign.screwsAllowance * qty;
    hardware += postsCost;
    hardware += screwsCost;
    components.push({
      label: `${$("posts_type").value} posts`,
      detail: `${qty} post set(s) at ${money(PRICING.sign.posts[$("posts_type").value] || 0)} each.`,
      amount: postsCost
    });
    components.push({
      label: "Screws / fasteners",
      detail: `${qty} hardware allowance at ${money(PRICING.sign.screwsAllowance)} each.`,
      amount: screwsCost
    });
  }
  if ($("pvc_cover_opt").checked) {
    const pvcCoverCost = PRICING.sign.pvcCover * qty;
    hardware += pvcCoverCost;
    components.push({
      label: "PVC post cover",
      detail: `${qty} cover set(s) at ${money(PRICING.sign.pvcCover)} each.`,
      amount: pvcCoverCost
    });
  }
  if ($("wall_mount_opt").checked) {
    const wallMountCost = (PRICING.sign.wallMount[$("wall_mount_type").value] || 0) * qty;
    hardware += wallMountCost;
    components.push({
      label: `${$("wall_mount_type").value} wall mount`,
      detail: `${qty} wall-mount hardware set(s) at ${money(PRICING.sign.wallMount[$("wall_mount_type").value] || 0)} each.`,
      amount: wallMountCost
    });
  }
  if ($("bucket_truck_opt").checked) {
    let bucketCost = PRICING.sign.bucketBase;
    let detail = `Bucket truck base charge is ${money(PRICING.sign.bucketBase)}.`;
    if (num("bucket_height") > 20) {
      const extraHeightCost = (num("bucket_height") - 20) * PRICING.sign.bucketPerFtOver20;
      bucketCost += extraHeightCost;
      detail += ` Height above 20 ft adds ${(num("bucket_height") - 20).toFixed(0)} ft at ${money(PRICING.sign.bucketPerFtOver20)} per foot.`;
    }
    hardware += bucketCost;
    components.push({ label: "Bucket truck", detail, amount: bucketCost });
  }
  return {
    rawTotal: hardware,
    markedUpTotal: hardware,
    components
  };
}

function renderSignPricingBreakdown(rows, autoPricingOn = true) {
  const list = $("pricing_breakdown_rows");
  const status = $("pricing_breakdown_status");
  if (!list || !status) return;

  if (!autoPricingOn) {
    status.textContent = "Manual";
    list.innerHTML = `
      <div class="breakdown-row">
        <div>
          <strong>Manual pricing enabled</strong>
          <small>Breakdown follows the values typed into the pricing fields.</small>
        </div>
        <div class="amount">${money(calcTotal())}</div>
      </div>`;
    return;
  }

  status.textContent = "Live";
  const safeRows = Array.isArray(rows) && rows.length ? rows : [{
    label: "Waiting for pricing input",
    detail: "Pick a substrate, graphics, or extras to see the math here.",
    amount: 0
  }];

  list.innerHTML = safeRows.map((row) => `
    <div class="breakdown-row">
      <div>
        <strong>${row.label}</strong>
        <small>${row.detail || ""}</small>
      </div>
      <div class="amount">${money(row.amount || 0)}</div>
    </div>`).join("");
}

function autoPriceSign() {
  const qty = Math.max(1, num("qty"));
  const sqftEach = calcSqft();
  const totalSqft = sqftEach * qty * ($("faces").value === "Double Sided" ? 2 : 1);
  const perimeterLf = calcTrimLinearFt() * qty;
  const substrate = PRICING.sign.substrates[$("substrate").value] || PRICING.sign.substrates.None;
  const signWasteMultiplier = 1 + PRICING.sign.signWastePercent;
  const smallJobWaste = totalSqft <= 12 ? PRICING.sign.extraSmallJobWastePercent : 0;
  const graphicsWasteMultiplier = 1 + PRICING.sign.graphicsWastePercent + smallJobWaste;
  const breakdownRows = [];

  let substratePrice = 0;
  if (substrate.type === "sheet" && substrate.cost > 0) {
    const usageRatio = totalSqft / PRICING.sign.sheetSqft;
    if (usageRatio < PRICING.sign.sheetPricingThreshold) {
      const sqftCost = substrate.cost / PRICING.sign.sheetSqft;
      substratePrice = totalSqft * sqftCost * PRICING.sign.substrateMarkup * signWasteMultiplier;
      breakdownRows.push({
        label: `Substrate charge: ${$("substrate").value} priced as a cut piece`,
        detail: `This job uses ${totalSqft.toFixed(2)} sq ft of ${$("substrate").value}. Because that is under ${(PRICING.sign.sheetPricingThreshold * 100).toFixed(0)}% of a full sheet, the app uses square-foot pricing: ${totalSqft.toFixed(2)} sq ft x ${money(sqftCost)}/sq ft x ${PRICING.sign.substrateMarkup.toFixed(2)} material markup x ${signWasteMultiplier.toFixed(2)} waste.`,
        amount: substratePrice
      });
    } else {
      const sheetCount = Math.max(1, Math.ceil(totalSqft / PRICING.sign.sheetSqft));
      substratePrice = sheetCount * substrate.cost * PRICING.sign.substrateMarkup * signWasteMultiplier;
      breakdownRows.push({
        label: `Substrate charge: ${$("substrate").value} priced as full sheet stock`,
        detail: `This job uses ${(usageRatio * 100).toFixed(1)}% of a sheet, so it is billed as ${sheetCount} full sheet at ${money(substrate.cost)} each, with ${PRICING.sign.substrateMarkup.toFixed(2)} material markup and ${signWasteMultiplier.toFixed(2)} waste.`,
        amount: substratePrice
      });
    }
  } else {
    breakdownRows.push({
      label: "Substrate charge",
      detail: "No substrate was selected, so no substrate charge was added.",
      amount: 0
    });
  }

  let graphicsPrice = 0;
  const graphicsMode = $("graphics_mode").value;
  if (graphicsMode === "DIGITAL") {
    const baseSqft = PRICING.sign.digitalSqftCost[$("digital_type").value] || 0;
    const laminateCost = $("laminate_opt").checked ? PRICING.sign.laminateSqftCost : 0;
    const digitalCost = (baseSqft + laminateCost + PRICING.sign.inkSqftCost + PRICING.sign.consumableSqftCost) * totalSqft * graphicsWasteMultiplier;
    graphicsPrice = (digitalCost * PRICING.sign.graphicsMarkup) + (num("item_digital") * PRICING.sign.digitalItemCharge);
    breakdownRows.push({
      label: `Graphics charge: Digital print (${ $("digital_type").value })`,
      detail: `Digital print materials total ${money(baseSqft + laminateCost + PRICING.sign.inkSqftCost + PRICING.sign.consumableSqftCost)}/sq ft, including media${$("laminate_opt").checked ? ", laminate" : ""}, ink, and consumables. The app applies that to ${totalSqft.toFixed(2)} sq ft, adds ${graphicsWasteMultiplier.toFixed(2)} waste, then uses a ${PRICING.sign.graphicsMarkup.toFixed(2)} graphics markup${num("item_digital") > 0 ? `. It also adds ${num("item_digital")} digital item charge at ${money(PRICING.sign.digitalItemCharge)} each` : ""}.`,
      amount: graphicsPrice
    });
  }
  if (graphicsMode === "VINYL") {
    const vinylCost = (PRICING.sign.vinylSqftCost[$("vinyl_type").value] || 0) + PRICING.sign.appTapeSqftCost + PRICING.sign.consumableSqftCost;
    graphicsPrice = (vinylCost * totalSqft * graphicsWasteMultiplier * PRICING.sign.graphicsMarkup) + (num("item_vinyl") * PRICING.sign.vinylItemCharge);
    breakdownRows.push({
      label: `Graphics charge: Cut vinyl (${ $("vinyl_type").value })`,
      detail: `Vinyl materials total ${money(vinylCost)}/sq ft, including film, application tape, and consumables. The app applies that to ${totalSqft.toFixed(2)} sq ft, adds ${graphicsWasteMultiplier.toFixed(2)} waste, then uses a ${PRICING.sign.graphicsMarkup.toFixed(2)} graphics markup${num("item_vinyl") > 0 ? `. It also adds ${num("item_vinyl")} vinyl item charge at ${money(PRICING.sign.vinylItemCharge)} each` : ""}.`,
      amount: graphicsPrice
    });
  }
  if (!graphicsMode) {
    breakdownRows.push({
      label: "Graphics charge",
      detail: "No digital print or vinyl graphics were selected, so no graphics charge was added.",
      amount: 0
    });
  }

  let designPrice = 0;
  if (num("design_hours") > 0) {
    designPrice = Math.max(PRICING.sign.designMinimum, num("design_hours") * PRICING.sign.designRate);
    breakdownRows.push({
      label: "Design and prep charge",
      detail: `Design time is billed at ${money(PRICING.sign.designRate)} per hour for ${num("design_hours").toFixed(2)} hour(s), with a minimum design charge of ${money(PRICING.sign.designMinimum)}.`,
      amount: designPrice
    });
  } else {
    breakdownRows.push({
      label: "Design and prep charge",
      detail: "No design hours were entered, so no design or prep charge was added.",
      amount: 0
    });
  }

  let installPrice = 0;
  const hasAdvancedInstall = $("bucket_truck_opt").checked || $("dig_opt").checked || $("wall_mount_opt").checked;
  const installRate = hasAdvancedInstall ? PRICING.sign.installAdvancedRate : PRICING.sign.installBaseRate;
  const laborHours = num("men") * num("man_hours");
  const travelCharge = calcTravelCharge(num("distance"), PRICING.sign);
  if (laborHours > 0 || num("distance") > 0 || $("posts_opt").checked || $("wall_mount_opt").checked) {
    installPrice = Math.max(PRICING.sign.installMinimum, (laborHours * installRate) + travelCharge);
    breakdownRows.push({
      label: "Install labor and travel charge",
      detail: `Install labor is ${laborHours.toFixed(2)} hour(s) at ${money(installRate)}${travelCharge > 0 ? `, plus ${money(travelCharge)} for travel` : ""}. If that total falls below the minimum install charge, the app uses ${money(PRICING.sign.installMinimum)} instead.`,
      amount: installPrice
    });
  } else {
    breakdownRows.push({
      label: "Install labor and travel charge",
      detail: "No install labor or travel inputs were entered, so no labor/travel charge was added.",
      amount: 0
    });
  }

  const hardwareResult = calcSignHardwareCharges(perimeterLf, qty, sqftEach);
  const hardwarePrice = hardwareResult.markedUpTotal;
  if (hardwareResult.components.length) {
    hardwareResult.components.forEach((component) => {
      breakdownRows.push({
        label: `Install hardware: ${component.label}`,
        detail: component.detail,
        amount: component.amount
      });
    });
  } else {
    breakdownRows.push({
      label: "Install hardware charge",
      detail: "No hardware options were selected, so no install hardware charge was added.",
      amount: 0
    });
  }
  let otherPrice = calcSignOtherCharges(perimeterLf);
  if ($("dig_opt").checked) otherPrice += (PRICING.sign.dig[$("dig_surface").value] || 0) * qty;

  const subtotal = substratePrice + graphicsPrice + designPrice + installPrice + hardwarePrice + otherPrice;
  const minimumAdjustment = Math.max(0, PRICING.sign.minimumCharge - subtotal);
  otherPrice += minimumAdjustment;
  breakdownRows.push({
    label: "Other charges and add-ons",
    detail: `${$("holes_opt").checked ? `Holes add ${money(PRICING.sign.holesCharge)}. ` : ""}${$("corners_opt").checked ? `Corners add ${money(PRICING.sign.cornersCharge)}. ` : ""}${$("grommets_opt").checked ? `Grommets are included in this line. ` : ""}${selectedOptions().includes("VELCRO") ? `Velcro adds ${money(PRICING.sign.velcroCharge)}. ` : ""}${selectedOptions().includes("D/S TAPE") ? `D/S tape adds ${money(PRICING.sign.tapeCharge)}. ` : ""}${$("dig_opt").checked ? `Dig charge is included for ${qty} sign${qty === 1 ? "" : "s"}. ` : ""}${minimumAdjustment > 0 ? `A minimum job adjustment of ${money(minimumAdjustment)} was added to reach the shop minimum.` : "No minimum job adjustment was needed."}`.trim(),
    amount: otherPrice
  });
  breakdownRows.push({
    label: "Final auto-priced total",
    detail: `This total covers ${totalSqft.toFixed(2)} sq ft across ${qty} sign${qty === 1 ? "" : "s"}${$("faces").value === "Double Sided" ? " and includes both sides" : ""}.`,
    amount: subtotal + minimumAdjustment
  });
  lastSignPricingBreakdown = breakdownRows;

  setNumberValue("p_substrate", substratePrice);
  setNumberValue("p_graphics", graphicsPrice);
  setNumberValue("p_fab", designPrice);
  setNumberValue("p_install", installPrice);
  setNumberValue("p_hardware", hardwarePrice);
  setNumberValue("p_other", otherPrice);

  $("pricing_note").textContent = `Auto pricing used ${totalSqft.toFixed(2)} sqft total. Minimum adjustment: ${money(minimumAdjustment)}.`;
  renderSignPricingBreakdown(breakdownRows, true);
}

function calcTotal() {
  return num("p_substrate") + num("p_graphics") + num("p_fab") + num("p_install") + num("p_hardware") + num("p_other");
}

function syncFrameTrimOptions() {
  const frameOn = $("frame_included").checked;
  const trimOn = $("trim_included").checked;

  $("frame_options").classList.toggle("show", frameOn);
  $("trim_options").classList.toggle("show", trimOn);

  if (!frameOn) {
    document.querySelectorAll(".frame-opt").forEach((el) => { el.checked = false; });
  }
  if (!trimOn) {
    document.querySelectorAll(".trim-opt").forEach((el) => { el.checked = false; });
  }
}

function syncExtrasOptions() {
  const holesOn = $("holes_opt").checked;
  const cornersOn = $("corners_opt").checked;
  const grommetsOn = $("grommets_opt").checked;
  const grommetsEveryX = $("grommets_pattern").value === "Every ___ Feet";
  $("holes_choice_row").classList.toggle("show", holesOn);
  $("corners_choice_row").classList.toggle("show", cornersOn);
  $("grommets_choice_row").classList.toggle("show", grommetsOn);
  $("grommets_spacing_wrap").classList.toggle("show", grommetsOn && grommetsEveryX);
  if (!grommetsOn || !grommetsEveryX) $("grommets_spacing").value = "1";
}

function syncGraphicsOptions() {
  const graphicsMode = $("graphics_mode").value;
  const digitalOn = graphicsMode === "DIGITAL";
  const vinylOn = graphicsMode === "VINYL";
  $("digital_choice_row").classList.toggle("show", digitalOn);
  $("laminate_label").classList.toggle("show", digitalOn);
  $("vinyl_choice_row").classList.toggle("show", vinylOn);
  $("digital_items_field").style.display = digitalOn ? "" : "none";
  $("vinyl_items_field").style.display = vinylOn ? "" : "none";
  if (!digitalOn) {
    $("laminate_opt").checked = false;
    $("item_digital").value = "0";
  }
  if (!vinylOn) $("item_vinyl").value = "0";
}

function syncInstallOptions() {
  const postsOn = $("posts_opt").checked;
  const digOn = $("dig_opt").checked;
  const wallMountOn = $("wall_mount_opt").checked;
  const bucketTruckOn = $("bucket_truck_opt").checked;

  $("posts_choice_row").classList.toggle("show", postsOn);
  $("pvc_cover_label").classList.toggle("show", postsOn);
  $("dig_label").classList.toggle("show", postsOn);
  $("dig_choice_row").classList.toggle("show", postsOn && digOn);
  $("wall_mount_choice_row").classList.toggle("show", wallMountOn);
  $("bucket_height_row").classList.toggle("show", bucketTruckOn);

  if (!postsOn) {
    $("pvc_cover_opt").checked = false;
    $("dig_opt").checked = false;
  }
  if (!bucketTruckOn) $("bucket_height").value = "0";
}

function renderWorkOrder() {
  calcSqft();
  calcTrimLinearFt();
  syncFrameTrimOptions();
  syncGraphicsOptions();
  syncExtrasOptions();
  syncInstallOptions();
  setPriceInputsLocked(["p_substrate", "p_graphics", "p_fab", "p_install", "p_hardware", "p_other"], $("auto_price").checked);
  if ($("auto_price").checked) autoPriceSign();
  const opts = [...selectedOptions(), ...selectedItems()];
  const total = calcTotal();

  $("wo_customer").textContent = `Customer: ${$("customer").value || "-"}`;
  $("wo_design").textContent = `Design: ${$("design").value || "-"}`;
  $("wo_date").textContent = `Date: ${$("date").value || "-"}`;
  $("wo_initials").textContent = `Initials: ${$("initials").value || "-"}`;
  $("wo_qty").textContent = `${$("qty").value || "0"} / ${$("faces").value || "-"}`;
  $("wo_size").textContent = `${$("width").value || "0"} x ${$("height").value || "0"} in / ${$("substrate").value || "-"}`;
  $("wo_sqft").textContent = $("sqft").value;
  $("wo_install").textContent = `${$("men").value || "0"} / ${$("man_hours").value || "0"} / ${$("distance").value || "0"} / ${$("design_hours").value || "0"}`;

  $("wo_opts").innerHTML = opts.length ? opts.map((o) => `<li>${o}</li>`).join("") : "<li>None</li>";

  $("wo_p_substrate").textContent = money(num("p_substrate"));
  $("wo_p_graphics").textContent = money(num("p_graphics"));
  $("wo_p_fab").textContent = money(num("p_fab"));
  $("wo_p_install").textContent = money(num("p_install"));
  $("wo_p_hardware").textContent = money(num("p_hardware"));
  $("wo_p_other").textContent = money(num("p_other"));
  $("wo_total").innerHTML = `<strong>${money(total)}</strong>`;

  $("wo_notes").textContent = $("notes").value.trim() || "-";
  if (!$("auto_price").checked) {
    $("pricing_note").textContent = "Manual pricing is on. Type any values you want in the pricing fields.";
  }
  renderSignPricingBreakdown(lastSignPricingBreakdown, $("auto_price").checked);
}

function calcVehicleTotal() {
  return num("vg_p_graphics") + num("vg_p_fab") + num("vg_p_install") + num("vg_p_hardware") + num("vg_p_removal") + num("vg_p_other");
}

function selectedVehicleOptions() {
  const items = [];
  const location = document.querySelector('input[name="vg_location"]:checked');
  if (location) items.push(`VEHICLE GRAPHICS (${location.value})`);
  ["vg_remove_existing", "vg_laminate", "vg_window_perf", "vg_install_only"].forEach((id) => {
    if ($(id).checked) items.push($(id).value);
  });
  if (num("vg_sqft") > 0) items.push(`SQFT / VEHICLE: ${num("vg_sqft").toFixed(2)}`);
  if (!$("vg_install_only").checked) items.push(`MEDIA: ${$("vg_media_type").selectedOptions[0].textContent.toUpperCase()}`);
  const instructions = $("vg_install_instructions").value.trim();
  if (instructions) items.push(`SPECIAL INSTRUCTIONS: ${instructions}`);
  return items;
}

function autoPriceVehicle() {
  const vehicleCount = Math.max(1, num("vg_vehicle_count"));
  const qty = Math.max(1, num("vg_qty"));
  const totalUnits = vehicleCount * qty;
  const sqftPerVehicle = num("vg_sqft");
  const installOnly = $("vg_install_only").checked;
  const mediaType = $("vg_window_perf").checked ? "window_perf" : $("vg_media_type").value;
  const serviceType = $("vg_service_type").value;

  let graphicsPrice = 0;
  if (!installOnly && sqftPerVehicle > 0) {
    graphicsPrice = sqftPerVehicle * totalUnits * (PRICING.vehicle.graphicsRates[mediaType] || 0);
  }

  let designPrice = 0;
  if (num("vg_design_hours") > 0) {
    designPrice = Math.max(PRICING.vehicle.standardDesignFee, num("vg_design_hours") * PRICING.vehicle.designRate);
  } else if (!installOnly && sqftPerVehicle > 0) {
    designPrice = PRICING.vehicle.templateSetupFee;
  }

  const installRate = (serviceType === "Full Wrap" || $("vg_location_onsite").checked) ? PRICING.vehicle.installAdvancedRate : PRICING.vehicle.installBaseRate;
  const installLabor = num("vg_men") * num("vg_man_hours") * installRate;
  const travelCharge = calcTravelCharge(num("vg_distance"), PRICING.vehicle);
  let installPrice = 0;
  if (installLabor > 0 || num("vg_distance") > 0 || $("vg_location_onsite").checked) {
    installPrice = Math.max(PRICING.vehicle.installMinimum, installLabor + travelCharge);
  }

  let hardwarePrice = 0;
  if (serviceType === "Full Wrap" || serviceType === "Partial Wrap") {
    hardwarePrice = PRICING.vehicle.hardwareFee * vehicleCount;
  }

  let removalPrice = 0;
  if ($("vg_remove_existing").checked) {
    removalPrice = Math.max(PRICING.vehicle.removalMinimum, num("vg_removal_hours") * PRICING.vehicle.removalRate);
  }

  let otherPrice = 0;
  if (!installOnly && (serviceType === "Full Wrap" || serviceType === "Partial Wrap" || $("vg_remove_existing").checked)) {
    otherPrice += PRICING.vehicle.surfacePrepFee * vehicleCount;
  }

  const subtotal = graphicsPrice + designPrice + installPrice + hardwarePrice + removalPrice + otherPrice;
  const minimumAdjustment = (!installOnly && subtotal > 0) ? Math.max(0, PRICING.vehicle.minimumCharge - subtotal) : 0;
  otherPrice += minimumAdjustment;

  setNumberValue("vg_p_graphics", graphicsPrice);
  setNumberValue("vg_p_fab", designPrice);
  setNumberValue("vg_p_install", installPrice);
  setNumberValue("vg_p_hardware", hardwarePrice);
  setNumberValue("vg_p_removal", removalPrice);
  setNumberValue("vg_p_other", otherPrice);

  $("vg_pricing_note").textContent = `Auto pricing used ${sqftPerVehicle.toFixed(2)} sqft per vehicle across ${totalUnits} unit(s). Minimum adjustment: ${money(minimumAdjustment)}.`;
}

function renderVehicleWorkOrder() {
  setPriceInputsLocked(["vg_p_graphics", "vg_p_fab", "vg_p_install", "vg_p_hardware", "vg_p_removal", "vg_p_other"], $("vg_auto_price").checked);
  if ($("vg_auto_price").checked) autoPriceVehicle();
  const total = calcVehicleTotal();
  const opts = selectedVehicleOptions();

  $("vg_wo_customer").textContent = `Customer: ${$("vg_customer").value || "-"}`;
  $("vg_wo_design").textContent = `Vehicle / Project: ${$("vg_design").value || "-"}`;
  $("vg_wo_date").textContent = `Date: ${$("vg_date").value || "-"}`;
  $("vg_wo_initials").textContent = `Initials: ${$("vg_initials").value || "-"}`;
  $("vg_wo_qty").textContent = `${$("vg_qty").value || "0"} / ${$("vg_vehicle_count").value || "0"}`;
  $("vg_wo_service").textContent = $("vg_service_type").value || "-";
  $("vg_wo_coverage").textContent = $("vg_coverage").value.trim() || "-";
  $("vg_wo_install").textContent = `${$("vg_men").value || "0"} / ${$("vg_man_hours").value || "0"} / ${$("vg_distance").value || "0"} / ${$("vg_design_hours").value || "0"}`;

  $("vg_wo_opts").innerHTML = opts.length ? opts.map((o) => `<li>${o}</li>`).join("") : "<li>None</li>";

  $("vg_wo_p_graphics").textContent = money(num("vg_p_graphics"));
  $("vg_wo_p_fab").textContent = money(num("vg_p_fab"));
  $("vg_wo_p_install").textContent = money(num("vg_p_install"));
  $("vg_wo_p_hardware").textContent = money(num("vg_p_hardware"));
  $("vg_wo_p_removal").textContent = money(num("vg_p_removal"));
  $("vg_wo_p_other").textContent = money(num("vg_p_other"));
  $("vg_wo_total").innerHTML = `<strong>${money(total)}</strong>`;

  $("vg_wo_notes").textContent = $("vg_notes").value.trim() || "-";
  if (!$("vg_auto_price").checked) {
    $("vg_pricing_note").textContent = "Manual pricing is on. Type any values you want in the vehicle pricing fields.";
  }
}

function clearForm(scope = document) {
  scope.querySelectorAll("input, select, textarea").forEach((el) => {
    if (el.type === "checkbox") el.checked = false;
    else if (el.type === "radio") el.checked = false;
    else if (el.type === "number") el.value = "0";
    else if (el.type === "date") el.value = "";
    else if (el.tagName === "SELECT") el.selectedIndex = 0;
    else el.value = "";
  });
  if (scope.querySelector("#qty")) {
    $("qty").value = "1";
    $("width").value = "24";
    $("height").value = "18";
    $("sqft").value = "3.00";
    $("auto_price").checked = true;
  }
  if (scope.querySelector("#vg_qty")) {
    $("vg_qty").value = "1";
    $("vg_vehicle_count").value = "1";
    $("vg_media_type").value = "printed_calendared";
    $("vg_auto_price").checked = true;
  }
  renderWorkOrder();
  renderVehicleWorkOrder();
}

function setActivePage(pageName) {
  const pages = ["signage", "vehicle"];
  const selected = pages.includes(pageName) ? pageName : "signage";
  $("page-signage").classList.toggle("hidden", selected !== "signage");
  $("page-vehicle").classList.toggle("hidden", selected !== "vehicle");
  document.querySelectorAll(".page-btn").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.page === selected);
  });
  try {
    localStorage.setItem("pricing_page", selected);
  } catch (e) {
    // Ignore storage errors.
  }
}

function initPagePicker() {
  let storedPage = "signage";
  try {
    storedPage = localStorage.getItem("pricing_page") || "signage";
  } catch (e) {
    storedPage = "signage";
  }
  setActivePage(storedPage);
  document.querySelectorAll(".page-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActivePage(btn.dataset.page));
  });
}

function setTheme(themeName) {
  const aliases = { industrial: "light", enterprise: "light", darkglass: "dark" };
  const normalized = aliases[themeName] || themeName;
  const themes = ["light", "dark"];
  const selected = themes.includes(normalized) ? normalized : "light";
  document.body.classList.remove("theme-light", "theme-dark");
  document.body.classList.add(`theme-${selected}`);
  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.theme === selected);
  });
  try {
    localStorage.setItem("pricing_theme", selected);
  } catch (e) {
    // Ignore storage errors in restricted/private contexts.
  }
}

function initThemePicker() {
  let storedTheme = "light";
  try {
    storedTheme = localStorage.getItem("pricing_theme") || "light";
  } catch (e) {
    storedTheme = "light";
  }
  setTheme(storedTheme);
  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.addEventListener("click", () => setTheme(btn.dataset.theme));
  });
}

document.querySelectorAll("#page-signage input, #page-signage select, #page-signage textarea").forEach((el) => {
  el.addEventListener("input", renderWorkOrder);
  el.addEventListener("change", renderWorkOrder);
});
document.querySelectorAll("#page-vehicle input, #page-vehicle select, #page-vehicle textarea").forEach((el) => {
  el.addEventListener("input", renderVehicleWorkOrder);
  el.addEventListener("change", renderVehicleWorkOrder);
});

$("recalc_sign").addEventListener("click", renderWorkOrder);
$("recalc_vehicle").addEventListener("click", renderVehicleWorkOrder);
$("print").addEventListener("click", () => window.print());
$("print_vehicle").addEventListener("click", () => window.print());
$("clear").addEventListener("click", () => clearForm($("page-signage")));
$("clear_vehicle").addEventListener("click", () => clearForm($("page-vehicle")));

initThemePicker();
initPagePicker();
renderWorkOrder();
renderVehicleWorkOrder();
