"""Live Qt smoke check; observer mode never interrupts another session.

--exercise prepares/starts its own session and clicks the actual red Stop button.
--freeze instead freezes GUI heartbeats to verify the independent backend watchdog.
"""
import argparse,json,threading,time
from pathlib import Path
import rclpy
from rclpy.executors import SingleThreadedExecutor
from python_qt_binding import QtWidgets
from uwa_cell_calibration.client import Client
from uwa_cell_calibration.gui import Window


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--screenshot');p.add_argument('--exercise',action='store_true');p.add_argument('--freeze',action='store_true')
    p.add_argument('--output');args=p.parse_args()
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    app=QtWidgets.QApplication([]);window=Window(node);window.show()
    def until(condition,seconds=20):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();time.sleep(.02)
            if condition():return
        raise TimeoutError(str(node.state)+' '+node.error)
    try:
        until(lambda:len(node.images)==4 and bool(node.state))
        assert window.count.minimum()==30 and window.count.maximum()==50
        assert window.stop_button.isEnabled() and 'bb1825' in window.stop_button.styleSheet()
        until(lambda:all(label.pixmap() is not None and not label.pixmap().isNull() for label in window.views.values()))
        result={'four_live_images':True,'red_stop_enabled':True,'count_range':[30,50]}
        if args.exercise or args.freeze:
            assert node.state['phase'] in ('IDLE','STOPPED','ERROR','READY','COMPLETE'), 'Another session is active'
            for rid,box in window.robots.items():box.setChecked(rid=='left_front')
            window.prepare_button.click()
            until(lambda:node.state.get('phase')=='READY' and node.state.get('client_id')==node.client_id,45)
            until(lambda:window.start_button.isEnabled())
            window.start_button.click();until(lambda:node.state.get('phase')=='MOVING')
            start=time.monotonic()
            if args.freeze:window.timer.stop()
            else:window.stop_button.click()
            until(lambda:node.state.get('phase')=='STOPPED' and node.state.get('stopped'),8)
            result.update(stopped=True,seconds_to_confirm=time.monotonic()-start,reason=node.state['message'])
            assert node.state.get('accepted',0)==0
            until(lambda:time.monotonic()-start>1)
            assert node.state['phase']=='STOPPED'
        if args.screenshot:
            app.processEvents();assert window.grab().save(args.screenshot)
        if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        window.allow_close=True;window.close();executor.shutdown(timeout_sec=2);node.destroy_node();rclpy.shutdown();thread.join(timeout=2)


if __name__=='__main__':main()
