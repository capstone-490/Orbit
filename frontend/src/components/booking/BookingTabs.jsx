import { useNavigate } from "react-router-dom";

function BookingTabs() {
  const navigate = useNavigate();

  return (
    <div className="booking-tabs">
      <button
        type="button"
        className="booking-tab"
        onClick={() => navigate("/login")}
      >
        Advisor Login
      </button>

      <button
        type="button"
        className="booking-tab active"
      >
        Book a Meeting
      </button>
    </div>
  );
}

export default BookingTabs;