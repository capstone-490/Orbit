// AI assistance: Used ChatGPT for implementation guidance and code refinement.

export default function AnimatedOrbitBackground() {
  return (
    <div className="welcome-sky" aria-hidden="true">
      <div className="welcome-track welcome-track-one">
        <div className="welcome-ring welcome-ring-one">
          <span className="welcome-planet welcome-planet-blue" />
        </div>
      </div>

      <div className="welcome-track welcome-track-two">
        <div className="welcome-ring welcome-ring-two">
          <span className="welcome-planet welcome-planet-green" />
          <span className="welcome-planet welcome-planet-blue welcome-planet-opposite" />
        </div>
      </div>

      <div className="welcome-track welcome-track-three">
        <div className="welcome-ring welcome-ring-three">
          <span className="welcome-planet welcome-planet-blue" />
        </div>
      </div>
    </div>
  );
}