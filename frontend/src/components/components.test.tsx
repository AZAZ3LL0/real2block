import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { FileDrop } from "./FileDrop";
import { SegmentedControl } from "./SegmentedControl";
import { Stepper } from "./Stepper";
import { WarningList } from "./WarningList";

function renderDrop() {
  const onFile = vi.fn();
  const onReject = vi.fn();
  render(
    <FileDrop label="Skin" hint="h" dropText="Drop" chooseText="choose" accept={["image/png"]} maxBytes={10} onFile={onFile} onReject={onReject} />,
  );
  const input = screen.getByLabelText<HTMLInputElement>("Skin");
  const pick = (file: File) => {
    fireEvent.change(input, { target: { files: [file] } });
  };
  return { onFile, onReject, pick };
}

describe("FileDrop", () => {
  it("accepts a valid file", () => {
    const { onFile, pick } = renderDrop();
    pick(new File(["png"], "s.png", { type: "image/png" }));
    expect(onFile).toHaveBeenCalledOnce();
  });

  it("rejects wrong type and oversize files", () => {
    const { onFile, onReject, pick } = renderDrop();
    pick(new File(["jpg"], "s.jpg", { type: "image/jpeg" }));
    pick(new File(["x".repeat(11)], "big.png", { type: "image/png" }));
    expect(onReject.mock.calls).toEqual([["type"], ["size"]]);
    expect(onFile).not.toHaveBeenCalled();
  });
});

describe("SegmentedControl", () => {
  it("is a radio group that reports the choice", async () => {
    const onChange = vi.fn();
    const options = [{ value: "a", label: "A" }, { value: "b", label: "B" }] as const;
    render(<SegmentedControl label="Pick" value="a" onChange={onChange} options={options} />);
    expect(screen.getByRole("radio", { name: "A" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "B" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });
});

describe("Stepper", () => {
  it("marks the current step", () => {
    render(<Stepper steps={["One", "Two"]} current={1} />);
    expect(screen.getByText("Two").closest("li")).toHaveAttribute("aria-current", "step");
  });
});

describe("WarningList", () => {
  it("shows human-readable warnings", () => {
    render(
      <I18nProvider initial="en">
        <WarningList warnings={["TORSO_NOT_VISIBLE"]} />
      </I18nProvider>,
    );
    expect(screen.getByText(/pick the shirt color manually/)).toBeInTheDocument();
  });
});
