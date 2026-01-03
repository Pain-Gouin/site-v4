// range-picker-bind.js
document.addEventListener("DOMContentLoaded", () => {
  // We look for all containers to support multiple widgets on one page
  const containers = document.querySelectorAll(".date-range-container");

  containers.forEach((container) => {
    const calendar = container.querySelector("calendar-range");
    // Django names MultiWidget inputs as [name]_0 and [name]_1
    const inputStart = container.querySelector('input[name$="_0"]');
    const inputEnd = container.querySelector('input[name$="_1"]');

    // Listen for changes on the calendar component
    calendar.addEventListener("change", (e) => {
      const value = e.target.value; // Format: "YYYY-MM-DD/YYYY-MM-DD"

      if (value && value.includes("/")) {
        const [start, end] = value.split("/");
        inputStart.value = start;
        inputEnd.value = end;
      } else {
        inputStart.value = "";
        inputEnd.value = "";
      }

      // Optional: Trigger a change event on the hidden inputs
      // in case other scripts are listening to them
      inputStart.dispatchEvent(new Event("change"));
      inputEnd.dispatchEvent(new Event("change"));
    });
  });
});
