import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, afterEach, vi } from "vitest";
import BookMeeting from "../pages/BookMeeting";

vi.mock("../components/booking/DateTimeStep", () => ({
  default: ({ onBack }) => (
    <div>
      <h2>Select Date & Time</h2>
      <button type="button" onClick={onBack}>
        Back to Session Type
      </button>
    </div>
  ),
}));

afterEach(cleanup);

describe("BookMeeting", () => {
  const renderBookMeeting = () =>
    render(
      <MemoryRouter>
        <BookMeeting />
      </MemoryRouter>
    );

  const goToDateTimeStep = () => {
    fireEvent.click(
      screen.getByRole("button", {
        name: /continue to date & time/i,
      })
    );
  };

  it("renders the booking page and meeting type options", () => {
    renderBookMeeting();

    const expectedTexts = [
      "What would you like to book?",
      "Introduction Meeting",
      "Continue My Financial Sessions",
      "Presentation 1 · Corporate Introduction",
      "Follow-up Consultation",
    ];

    expectedTexts.forEach((text) => {
      expect(screen.getByText(text)).toBeInTheDocument();
    });
  });

  it("allows the user to select a meeting type", () => {
    renderBookMeeting();

    const followUpCard = screen
      .getByText("Continue My Financial Sessions")
      .closest("button");

    fireEvent.click(followUpCard);

    expect(followUpCard).toHaveClass("selected");
  });

  it("moves from step 1 to step 2", () => {
    renderBookMeeting();

    goToDateTimeStep();

    expect(
      screen.getByText("Select Date & Time")
    ).toBeInTheDocument();

    expect(
      screen.queryByText("What would you like to book?")
    ).not.toBeInTheDocument();
  });

  it("returns from step 2 to step 1", () => {
    renderBookMeeting();

    goToDateTimeStep();

    fireEvent.click(
      screen.getByRole("button", {
        name: /back to session type/i,
      })
    );

    expect(
      screen.getByText("What would you like to book?")
    ).toBeInTheDocument();
  });
});